from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from workflow_core import (
    DEFAULT_OUTPUT_DIR,
    ROOT,
    build_render_context,
    configure_stdio,
    deep_merge_dict,
    get_missing_requirements,
    list_workflow_definitions,
    load_workflow_definition,
    load_yaml_dict,
    now_iso,
    nested_set,
    parse_workflow_response,
    render_prompt_template,
    slugify,
    write_text,
    write_yaml_file,
)


STUDIO_DIR = ROOT / "studio"
SESSIONS_DIR = DEFAULT_OUTPUT_DIR / "studio-sessions"


def main() -> None:
    configure_stdio()
    parser = argparse.ArgumentParser(
        prog="workflow_studio.py",
        description="本地工作流可视化编辑器",
    )
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    args = parser.parse_args()

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), WorkflowStudioHandler)
    print(f"工作流工作台已启动：http://{args.host}:{args.port}")
    server.serve_forever()


def build_workflow_summary(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": workflow["id"],
        "name": workflow["name"],
        "description": workflow.get("description", ""),
        "input_template": workflow.get("input_template"),
        "field_labels": workflow.get("field_labels", {}),
        "field_placeholders": workflow.get("field_placeholders", {}),
        "field_help": workflow.get("field_help", {}),
        "steps": [
            {
                "id": step["id"],
                "index": step["index"],
                "title": step["title"],
                "required_before_generate": step.get("required_before_generate", []),
                "response_target": step.get("response_target", ""),
                "response_target_label": step.get("response_target_label", ""),
                "extra_output_blocks": step.get("extra_output_blocks", []),
            }
            for step in workflow["steps"]
        ],
    }


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def session_state_path(session_id: str) -> Path:
    return session_dir(session_id) / "state.json"


def session_input_path(session_id: str) -> Path:
    return session_dir(session_id) / "input.yaml"


def load_session_state(session_id: str) -> dict[str, Any]:
    path = session_state_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"找不到会话：{session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_session_state(state: dict[str, Any]) -> None:
    current_id = state["session_id"]
    state["updated_at"] = now_iso()
    base_dir = session_dir(current_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    session_state_path(current_id).write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_yaml_file(session_input_path(current_id), state["data"])


def session_payload(state: dict[str, Any], workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": state["session_id"],
        "workflow": build_workflow_summary(workflow),
        "workflow_id": state["workflow_id"],
        "workflow_name": state["workflow_name"],
        "created_at": state["created_at"],
        "updated_at": state["updated_at"],
        "current_step_id": state.get("current_step_id"),
        "data": state["data"],
        "steps": state["steps"],
    }


def list_sessions() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not SESSIONS_DIR.exists():
        return items
    for path in SESSIONS_DIR.glob("*/state.json"):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "session_id": state["session_id"],
                "workflow_id": state["workflow_id"],
                "workflow_name": state["workflow_name"],
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
                "current_step_id": state.get("current_step_id"),
            }
        )
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return items


def create_session(workflow_id: str) -> dict[str, Any]:
    workflow = load_workflow_definition(workflow_id)
    template_path = ROOT / str(workflow["input_template"])
    data = load_yaml_dict(template_path)
    defaults = workflow.get("state_defaults", {})
    if isinstance(defaults, dict):
        data = deep_merge_dict(data, defaults)

    created_at = now_iso()
    session_id = f"{Path(created_at.replace(':', '').replace('T', '-')).name}-{slugify(workflow_id)}"
    steps: dict[str, Any] = {}
    for step in workflow["steps"]:
        steps[step["id"]] = {
            "id": step["id"],
            "index": step["index"],
            "title": step["title"],
            "status": "pending",
            "prompt_file": step["prompt_file"],
            "response_file": step["response_file"],
            "primary_output_file": step["primary_output_file"],
            "prompt_text": "",
            "response_text": "",
            "primary_content": "",
            "extra_outputs": {},
            "parsed_metadata": {},
            "parsed_json": None,
            "parse_error": "",
            "generated_at": "",
            "completed_at": "",
        }

    state = {
        "session_id": session_id,
        "workflow_id": workflow["id"],
        "workflow_name": workflow["name"],
        "created_at": created_at,
        "updated_at": created_at,
        "current_step_id": workflow["steps"][0]["id"],
        "data": data,
        "steps": steps,
    }
    save_session_state(state)
    return session_payload(state, workflow)


def get_step(workflow: dict[str, Any], step_id: str) -> dict[str, Any]:
    for step in workflow["steps"]:
        if step["id"] == step_id:
            return step
    raise KeyError(step_id)


def next_step_id(workflow: dict[str, Any], step_id: str) -> str | None:
    step_ids = [step["id"] for step in workflow["steps"]]
    try:
        index = step_ids.index(step_id)
    except ValueError:
        return None
    if index + 1 >= len(step_ids):
        return None
    return step_ids[index + 1]


def render_step_prompt(
    state: dict[str, Any],
    workflow: dict[str, Any],
    step_id: str,
) -> dict[str, Any]:
    step = get_step(workflow, step_id)
    missing = get_missing_requirements(state["data"], step.get("required_before_generate", []))
    if missing:
        return {"ready": False, "missing": missing}

    prompt_text = render_prompt_template(step["prompt_path"], build_render_context(state["data"]))
    base_dir = session_dir(state["session_id"])
    write_text(base_dir / step["prompt_file"], prompt_text)

    current_step = state["steps"][step_id]
    current_step["prompt_text"] = prompt_text
    current_step["status"] = "prompt_ready"
    current_step["generated_at"] = now_iso()
    current_step["parse_error"] = ""
    return {"ready": True, "step": current_step}


def parse_and_store_response(
    state: dict[str, Any],
    workflow: dict[str, Any],
    step_id: str,
    response_text: str,
) -> dict[str, Any]:
    step = get_step(workflow, step_id)
    current_step = state["steps"][step_id]
    base_dir = session_dir(state["session_id"])
    write_text(base_dir / step["response_file"], response_text)
    current_step["response_text"] = response_text

    parsed = parse_workflow_response(response_text)
    metadata = parsed["metadata"]
    if metadata.get("step_id") and metadata["step_id"] != step_id:
        raise ValueError(f"step_id 不匹配，期望 {step_id}，实际 {metadata['step_id']}")

    primary_content = parsed["primary_content"]
    write_text(base_dir / step["primary_output_file"], primary_content + "\n")

    target_path = step.get("response_target")
    if target_path:
        nested_set(state["data"], target_path, primary_content)

    extra_outputs: dict[str, str] = {}
    parsed_named_blocks = parsed.get("named_blocks", {})
    for block in step.get("extra_output_blocks", []):
        block_id = block.get("id")
        if not block_id:
            continue
        if block_id not in parsed_named_blocks:
            raise ValueError(f"缺少附加输出块：{block_id}")
        block_content = parsed_named_blocks[block_id]
        output_file = block.get("output_file")
        if output_file:
            write_text(base_dir / str(output_file), block_content + "\n")
        target_path = block.get("target_path")
        if target_path:
            nested_set(state["data"], str(target_path), block_content)
        extra_outputs[block_id] = block_content

    current_step["primary_content"] = primary_content
    current_step["extra_outputs"] = extra_outputs
    current_step["parsed_metadata"] = metadata
    current_step["parsed_json"] = parsed["structured_json"]
    current_step["parse_error"] = ""
    current_step["status"] = "completed"
    current_step["completed_at"] = now_iso()

    next_id = next_step_id(workflow, step_id)
    state["current_step_id"] = next_id or step_id
    result: dict[str, Any] = {
        "step": current_step,
        "next_step_id": next_id,
    }

    if next_id:
        next_prompt = render_step_prompt(state, workflow, next_id)
        result["next_step"] = next_prompt

    return result


class WorkflowStudioHandler(BaseHTTPRequestHandler):
    server_version = "WorkflowStudio/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self.send_json({"ok": True})
            return
        if path == "/api/workflows":
            workflows = [build_workflow_summary(item) for item in list_workflow_definitions()]
            self.send_json({"workflows": workflows})
            return
        if path == "/api/sessions":
            self.send_json({"sessions": list_sessions()})
            return
        if path.startswith("/api/sessions/"):
            session_id = path.removeprefix("/api/sessions/")
            try:
                state = load_session_state(session_id)
                workflow = load_workflow_definition(state["workflow_id"])
            except FileNotFoundError:
                self.send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            self.send_json(session_payload(state, workflow))
            return

        self.serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        if path == "/api/sessions":
            workflow_id = str(body.get("workflow_id") or "article-to-platform")
            payload = create_session(workflow_id)
            self.send_json(payload, status=HTTPStatus.CREATED)
            return

        if path.startswith("/api/sessions/") and path.endswith("/autosave"):
            session_id = path.split("/")[3]
            try:
                state = load_session_state(session_id)
                workflow = load_workflow_definition(state["workflow_id"])
            except FileNotFoundError:
                self.send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return

            data = body.get("data")
            if not isinstance(data, dict):
                self.send_json({"error": "invalid_data"}, status=HTTPStatus.BAD_REQUEST)
                return
            state["data"] = data
            current_step_id = body.get("current_step_id")
            if current_step_id:
                state["current_step_id"] = str(current_step_id)
            step_responses = body.get("step_responses")
            if isinstance(step_responses, dict):
                for step_id, response_text in step_responses.items():
                    if step_id not in state["steps"] or not isinstance(response_text, str):
                        continue
                    state["steps"][step_id]["response_text"] = response_text
            save_session_state(state)
            self.send_json(session_payload(state, workflow))
            return

        if "/steps/" in path and path.endswith("/prompt"):
            session_id, step_id = extract_session_and_step(path, "prompt")
            try:
                state = load_session_state(session_id)
                workflow = load_workflow_definition(state["workflow_id"])
            except FileNotFoundError:
                self.send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return

            result = render_step_prompt(state, workflow, step_id)
            save_session_state(state)
            if not result["ready"]:
                self.send_json(
                    {
                        "error": "missing_required_fields",
                        "message": f"生成当前步骤提示词前还缺少字段：{', '.join(result['missing'])}",
                        "ready": False,
                        "missing": result["missing"],
                        "session": session_payload(state, workflow),
                    },
                    status=HTTPStatus.CONFLICT,
                )
                return
            self.send_json(
                {
                    "ready": True,
                    "step": state["steps"][step_id],
                    "session": session_payload(state, workflow),
                }
            )
            return

        if "/steps/" in path and path.endswith("/response"):
            session_id, step_id = extract_session_and_step(path, "response")
            try:
                state = load_session_state(session_id)
                workflow = load_workflow_definition(state["workflow_id"])
            except FileNotFoundError:
                self.send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return

            response_text = body.get("response_text")
            if not isinstance(response_text, str) or not response_text.strip():
                self.send_json(
                    {"error": "empty_response_text"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            try:
                result = parse_and_store_response(state, workflow, step_id, response_text)
            except ValueError as exc:
                state["steps"][step_id]["parse_error"] = str(exc)
                state["steps"][step_id]["status"] = "parse_error"
                save_session_state(state)
                self.send_json(
                    {
                        "error": "parse_failed",
                        "message": str(exc),
                        "session": session_payload(state, workflow),
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return

            save_session_state(state)
            self.send_json(
                {
                    "ok": True,
                    "result": result,
                    "session": session_payload(state, workflow),
                }
            )
            return

        self.send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        payload = self.rfile.read(length).decode("utf-8")
        if not payload.strip():
            return {}
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("JSON body 必须是对象。")
        return data

    def serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STUDIO_DIR / relative).resolve()
        if not str(target).startswith(str(STUDIO_DIR.resolve())) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"

        payload = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def extract_session_and_step(path: str, endpoint: str) -> tuple[str, str]:
    parts = [part for part in path.split("/") if part]
    if len(parts) != 6:
        raise ValueError(f"路径格式不正确：{path}")
    return parts[2], parts[4]


if __name__ == "__main__":
    main()
