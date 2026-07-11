const state = {
  workflows: [],
  sessions: [],
  currentSession: null,
  activeStepId: null,
  autosaveTimer: null,
};

const elements = {
  workflowSelect: document.getElementById("workflowSelect"),
  createSessionButton: document.getElementById("createSessionButton"),
  refreshSessionsButton: document.getElementById("refreshSessionsButton"),
  sessionList: document.getElementById("sessionList"),
  sessionTitle: document.getElementById("sessionTitle"),
  autosaveStatus: document.getElementById("autosaveStatus"),
  manualSaveButton: document.getElementById("manualSaveButton"),
  formRoot: document.getElementById("formRoot"),
  stepList: document.getElementById("stepList"),
  activeStepTitle: document.getElementById("activeStepTitle"),
  stepMeta: document.getElementById("stepMeta"),
  promptOutput: document.getElementById("promptOutput"),
  responseInput: document.getElementById("responseInput"),
  parseResult: document.getElementById("parseResult"),
  extractedOutput: document.getElementById("extractedOutput"),
  generatePromptButton: document.getElementById("generatePromptButton"),
  copyPromptButton: document.getElementById("copyPromptButton"),
  submitResponseButton: document.getElementById("submitResponseButton"),
};

const STATUS_LABELS = {
  pending: "未开始",
  prompt_ready: "提示词已生成",
  completed: "已完成",
  parse_error: "解析失败",
};

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const payload = await response.json();
  if (!response.ok) {
    const missingText = Array.isArray(payload.missing) && payload.missing.length
      ? `缺少字段：${payload.missing.join(", ")}`
      : "";
    const message = payload.message || missingText || payload.error || `请求失败：${response.status}`;
    throw new Error(message);
  }
  return payload;
}

function formatStatus(status) {
  return STATUS_LABELS[status] || status || "未知状态";
}

function getFieldLabels() {
  return getWorkflow()?.field_labels || {};
}

function getFieldPlaceholders() {
  return getWorkflow()?.field_placeholders || {};
}

function getFieldHelp() {
  return getWorkflow()?.field_help || {};
}

function formatFieldLabel(path) {
  const dottedPath = path.join(".");
  const labels = getFieldLabels();
  return labels[dottedPath] || path[path.length - 1] || dottedPath;
}

function formatFieldPlaceholder(path) {
  const dottedPath = path.join(".");
  const placeholders = getFieldPlaceholders();
  return placeholders[dottedPath] || "";
}

function formatFieldHelp(path) {
  const dottedPath = path.join(".");
  const help = getFieldHelp();
  return help[dottedPath] || "";
}

function formatTargetLabel(step) {
  return step.response_target_label || step.response_target || "无";
}

function setAutosaveStatus(text) {
  elements.autosaveStatus.textContent = text;
}

function setAtPath(target, path, value) {
  let current = target;
  for (let index = 0; index < path.length - 1; index += 1) {
    const key = path[index];
    if (!current[key] || typeof current[key] !== "object" || Array.isArray(current[key])) {
      current[key] = {};
    }
    current = current[key];
  }
  current[path[path.length - 1]] = value;
}

function getWorkflow() {
  return state.currentSession ? state.currentSession.workflow : null;
}

function getActiveStep() {
  if (!state.currentSession || !state.activeStepId) {
    return null;
  }
  return state.currentSession.steps[state.activeStepId] || null;
}

function formatTime(isoString) {
  if (!isoString) {
    return "未记录";
  }
  return isoString.replace("T", " ");
}

function scheduleAutosave() {
  if (!state.currentSession) {
    return;
  }
  setAutosaveStatus("待自动保存");
  clearTimeout(state.autosaveTimer);
  state.autosaveTimer = setTimeout(() => {
    saveCurrentSession();
  }, 700);
}

async function loadWorkflows() {
  const payload = await request("/api/workflows");
  state.workflows = payload.workflows;
  elements.workflowSelect.innerHTML = "";
  for (const workflow of state.workflows) {
    const option = document.createElement("option");
    option.value = workflow.id;
    option.textContent = workflow.name;
    elements.workflowSelect.append(option);
  }
}

async function loadSessions() {
  const payload = await request("/api/sessions");
  state.sessions = payload.sessions;
  renderSessionList();
}

function renderSessionList() {
  elements.sessionList.innerHTML = "";
  if (!state.sessions.length) {
    elements.sessionList.innerHTML = "<p class='subtle'>还没有会话。</p>";
    return;
  }

  for (const session of state.sessions) {
    const wrapper = document.createElement("div");
    wrapper.className = "session-item";
    if (state.currentSession && state.currentSession.session_id === session.session_id) {
      wrapper.classList.add("active");
    }

    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `
      <strong>${session.workflow_name}</strong>
      <div class="session-meta">
        <div>${session.session_id}</div>
        <div>更新于 ${formatTime(session.updated_at)}</div>
      </div>
    `;
    button.addEventListener("click", () => {
      openSession(session.session_id);
    });

    wrapper.append(button);
    elements.sessionList.append(wrapper);
  }
}

async function createSession() {
  const workflowId = elements.workflowSelect.value;
  const payload = await request("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ workflow_id: workflowId }),
  });
  state.currentSession = payload;
  state.activeStepId = payload.current_step_id || payload.workflow.steps[0]?.id || null;
  setAutosaveStatus("已创建");
  await loadSessions();
  renderAll();
}

async function openSession(sessionId) {
  const payload = await request(`/api/sessions/${sessionId}`);
  state.currentSession = payload;
  state.activeStepId = payload.current_step_id || payload.workflow.steps[0]?.id || null;
  setAutosaveStatus("已加载");
  renderAll();
}

function renderAll() {
  renderHeader();
  renderForm();
  renderStepList();
  renderActiveStep();
}

function renderHeader() {
  if (!state.currentSession) {
    elements.sessionTitle.textContent = "未选择";
    return;
  }
  elements.sessionTitle.textContent = `${state.currentSession.workflow_name} / ${state.currentSession.session_id}`;
}

function renderForm() {
  const root = elements.formRoot;
  root.innerHTML = "";

  if (!state.currentSession) {
    root.innerHTML = "<p class='subtle'>先创建或打开一个会话。</p>";
    return;
  }

  const entries = Object.entries(state.currentSession.data);
  for (const [key, value] of entries) {
    root.append(renderValueEditor(key, value, [key], 3));
  }
}

function renderValueEditor(label, value, path, headingLevel = 4) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const section = document.createElement("section");
    section.className = "field-group";
    const title = document.createElement(`h${headingLevel}`);
    title.textContent = formatFieldLabel(path);
    section.append(title);
    for (const [childKey, childValue] of Object.entries(value)) {
      section.append(renderValueEditor(childKey, childValue, [...path, childKey], Math.min(headingLevel + 1, 6)));
    }
    return section;
  }

  const field = document.createElement("div");
  field.className = "field";
  const labelElement = document.createElement("label");
  labelElement.className = "label";
  labelElement.textContent = formatFieldLabel(path);
  field.append(labelElement);

  let input;
  if (Array.isArray(value)) {
    input = document.createElement("textarea");
    input.value = value.join("\n");
    input.dataset.kind = "array";
  } else if (typeof value === "boolean") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = value;
    input.dataset.kind = "boolean";
  } else if (typeof value === "string" && (value.includes("\n") || value.length > 50 || /article|notes|draft|focus|constraints/i.test(path[path.length - 1]))) {
    input = document.createElement("textarea");
    input.value = value;
    input.dataset.kind = "string";
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.value = value ?? "";
    input.dataset.kind = "string";
  }

  const placeholder = formatFieldPlaceholder(path);
  if (placeholder) {
    input.placeholder = placeholder;
  }
  input.dataset.path = JSON.stringify(path);
  input.addEventListener("input", onFieldInput);
  if (input.type === "checkbox") {
    input.addEventListener("change", onFieldInput);
  }
  field.append(input);

  const helpText = formatFieldHelp(path);
  if (helpText) {
    const helpElement = document.createElement("small");
    helpElement.textContent = helpText;
    field.append(helpElement);
  }
  return field;
}

function onFieldInput(event) {
  if (!state.currentSession) {
    return;
  }
  const input = event.currentTarget;
  const path = JSON.parse(input.dataset.path);
  let value;
  if (input.dataset.kind === "array") {
    value = input.value
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
  } else if (input.dataset.kind === "boolean") {
    value = Boolean(input.checked);
  } else {
    value = input.value;
  }
  setAtPath(state.currentSession.data, path, value);
  scheduleAutosave();
}

async function saveCurrentSession() {
  if (!state.currentSession) {
    return;
  }
  setAutosaveStatus("保存中");
  const stepResponses = Object.fromEntries(
    Object.entries(state.currentSession.steps).map(([stepId, step]) => [
      stepId,
      step.response_text || "",
    ]),
  );
  const payload = await request(`/api/sessions/${state.currentSession.session_id}/autosave`, {
    method: "POST",
    body: JSON.stringify({
      data: state.currentSession.data,
      current_step_id: state.activeStepId,
      step_responses: stepResponses,
    }),
  });
  state.currentSession = payload;
  setAutosaveStatus(`已保存 ${formatTime(payload.updated_at)}`);
  await loadSessions();
  renderAll();
}

function renderStepList() {
  const root = elements.stepList;
  root.innerHTML = "";
  if (!state.currentSession) {
    root.innerHTML = "<p class='subtle'>未打开会话。</p>";
    return;
  }

  for (const step of state.currentSession.workflow.steps) {
    const sessionStep = state.currentSession.steps[step.id];
    const wrapper = document.createElement("div");
    wrapper.className = "step-item";
    if (step.id === state.activeStepId) {
      wrapper.classList.add("active");
    }

    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = `
      <div class="section-head">
        <strong>${step.index}. ${step.title}</strong>
        <span class="badge ${sessionStep.status}">${formatStatus(sessionStep.status)}</span>
      </div>
      <div class="step-meta">
        <div>本步产物：${formatTargetLabel(step)}</div>
        <div>最近生成：${formatTime(sessionStep.generated_at)}</div>
      </div>
    `;
    button.addEventListener("click", () => {
      state.activeStepId = step.id;
      renderActiveStep();
      renderStepList();
    });

    wrapper.append(button);
    root.append(wrapper);
  }
}

function renderActiveStep() {
  const step = getActiveStep();
  if (!state.currentSession || !step) {
    elements.activeStepTitle.textContent = "未选择步骤";
    elements.stepMeta.innerHTML = "";
    elements.promptOutput.value = "";
    elements.responseInput.value = "";
    elements.parseResult.textContent = "";
    elements.extractedOutput.value = "";
    return;
  }

  elements.activeStepTitle.textContent = `${step.index}. ${step.title}`;
  elements.promptOutput.value = step.prompt_text || "";
  elements.responseInput.value = step.response_text || "";
  elements.extractedOutput.value = step.primary_content || "";
  elements.parseResult.textContent = JSON.stringify(
    {
      步骤状态: formatStatus(step.status),
      解析错误: step.parse_error || null,
      解析元数据: step.parsed_metadata || {},
      结构化数据: step.parsed_json || null,
      附加输出: step.extra_outputs || {},
    },
    null,
    2,
  );

  const workflowStep = getWorkflow().steps.find((item) => item.id === step.id);
  elements.stepMeta.innerHTML = `
    <span class="badge ${step.status}">${formatStatus(step.status)}</span>
    <span class="badge">本步产物：${formatTargetLabel(workflowStep)}</span>
    <span class="badge">提示词和回填内容会自动保存到当前会话目录</span>
  `;
}

function onResponseInput(event) {
  const step = getActiveStep();
  if (!state.currentSession || !step) {
    return;
  }
  state.currentSession.steps[step.id].response_text = event.currentTarget.value;
  scheduleAutosave();
}

async function generatePrompt() {
  const step = getActiveStep();
  if (!state.currentSession || !step) {
    return;
  }
  await saveCurrentSession();
  try {
    const payload = await request(
      `/api/sessions/${state.currentSession.session_id}/steps/${step.id}/prompt`,
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
    state.currentSession = payload.session;
    renderAll();
    setAutosaveStatus("提示词已生成");
  } catch (error) {
    setAutosaveStatus("生成失败");
    alert(`生成提示词失败：${error.message}`);
  }
}

async function submitResponse() {
  const step = getActiveStep();
  if (!state.currentSession || !step) {
    return;
  }
  try {
    const payload = await request(
      `/api/sessions/${state.currentSession.session_id}/steps/${step.id}/response`,
      {
        method: "POST",
        body: JSON.stringify({ response_text: elements.responseInput.value }),
      },
    );
    state.currentSession = payload.session;
    if (payload.result.next_step_id) {
      state.activeStepId = payload.result.next_step_id;
    }
    renderAll();
    setAutosaveStatus("已解析并保存");
  } catch (error) {
    setAutosaveStatus("解析失败");
    alert(`保存或解析失败：${error.message}`);
  }
}

async function copyPrompt() {
  if (!elements.promptOutput.value.trim()) {
    return;
  }
  await navigator.clipboard.writeText(elements.promptOutput.value);
  setAutosaveStatus("提示词已复制");
}

function bindEvents() {
  elements.createSessionButton.addEventListener("click", createSession);
  elements.refreshSessionsButton.addEventListener("click", loadSessions);
  elements.manualSaveButton.addEventListener("click", saveCurrentSession);
  elements.generatePromptButton.addEventListener("click", generatePrompt);
  elements.submitResponseButton.addEventListener("click", submitResponse);
  elements.copyPromptButton.addEventListener("click", copyPrompt);
  elements.responseInput.addEventListener("input", onResponseInput);
}

async function bootstrap() {
  bindEvents();
  await loadWorkflows();
  await loadSessions();
  if (state.sessions[0]) {
    await openSession(state.sessions[0].session_id);
  }
}

bootstrap();
