# ai_workflow_kit

一个面向文章整理与多平台成稿场景的模板合并工作流仓库。

当前版本使用 `uv + Python` 自动把输入字段合并进 prompt 模板，并把结果写入 `outputs/`，不直接调用大模型 API。

现在额外提供一个本地可视化版本 `Workflow Studio`：

- 表单编辑当前输入
- 自动保存到仓库会话目录
- 按工作流步骤生成 prompt
- 粘贴 AI 输出后自动解析
- 自动写回下一步所需字段，并生成下一步 prompt

## 这个仓库现在做什么

把一篇输入文章的要求整理清楚，并生成四个阶段的“已合并模板结果”，供你后续继续使用，同时严格保留原意相关约束。

## 当前原则

- 严格保留原意
- 不补充原文没有的信息
- 平台、风格、长度、输出项等全部作为输入字段
- 当前只负责模板合并，不负责模型生成

## 最小目录结构

```text
ai_workflow_kit/
├── README.md
├── .gitignore
├── config/
│   └── platform-rules.yaml
├── pyproject.toml
├── prompts/
│   ├── article-structuring.md
│   ├── platform-copywriting.md
│   ├── platform-copy-review.md
│   └── final-article-writing.md
├── scripts/
│   └── run_workflow.py
├── workflows/
│   └── article-to-platform-workflow.md
└── templates/
    └── article-to-platform-input.example.yaml
```

## 怎么安装

1. 安装依赖：

```bash
uv sync
```

## 怎么用

### 非技术方案

适合直接手动使用 prompt 的场景。

1. 先填写 `templates/article-to-platform-input.example.yaml`，通常至少只需要补 `source_article`，其他字段按需补充。
2. 打开 `prompts/article-structuring.md`，整理原始文章。
3. 保存整理结果，作为后续平台成稿的中间材料。
4. 打开 `prompts/platform-copywriting.md`，把中间材料转换成目标平台文稿。
5. 检查标题、正文、结尾和标签是否符合本次平台要求。
6. 打开 `prompts/platform-copy-review.md`，对原文、整理材料和平台文稿做一轮对照检查，得到审查报告。
7. 打开 `prompts/final-article-writing.md`，把原文、整理材料、平台文稿和审查报告统一交给最终写作助手生成终稿。
8. 如有需要，再做最后一轮人工微调。

### 技术方案

适合先把输入字段和模板自动合并出来，再继续处理的场景。

1. 生成一份输入模板：

```bash
uv run python scripts/run_workflow.py init
```

默认会生成 `inputs/article-to-platform-input.yaml`。

2. 填写输入 YAML。现在通常只要贴入原文并确认 `target_platform`；脚本会自动把对应平台预设规则注入 prompt，只有你想更精确控制时再补其他字段。

3. 如有需要，可在输入 YAML 的中间字段中补充“整理后的文章材料”或“平台文稿”。

4. 运行模板合并：

```bash
uv run python scripts/run_workflow.py run --input inputs/article-to-platform-input.yaml
```

5. 脚本会先根据 `target_platform` 命中 `config/platform-rules.yaml` 中的预设规则，再自动完成四份 prompt 模板的字段合并：

- 整理原文 prompt 合并
- 平台成稿 prompt 合并
- 文稿复核 prompt 合并
- 最终写作 prompt 合并

6. 到 `outputs/<时间戳-平台名>/` 中查看合并后的结果文件。

## 你会得到什么

每次运行后，`outputs/` 下会生成一组文件：

- `01-article-structuring.merged.txt`
- `02-platform-copywriting.merged.txt`
- `03-platform-copy-review.merged.txt`
- `04-final-article-writing.merged.txt`
- `run-summary.json`

## 常用命令

初始化输入模板：

```bash
uv run python scripts/run_workflow.py init --force
```

执行完整流程：

```bash
uv run python scripts/run_workflow.py run --input inputs/article-to-platform-input.yaml
```

启动本地可视化版本：

```bash
uv run python scripts/workflow_studio.py
```

默认地址：

```text
http://127.0.0.1:8765
```

## Workflow Studio 第一版怎么用

1. 启动 `Workflow Studio`。
2. 新建一个工作流会话。
3. 在页面里填表，内容会自动保存到 `outputs/studio-sessions/<session-id>/input.yaml`。
4. 选择当前步骤，点击“生成 Prompt”。
5. 复制 Prompt 去问 AI。
6. 把 AI 完整输出粘贴回页面；粘贴区草稿也会自动保存。
7. 点击“保存并解析”。
8. 系统会自动把本步主结果写回会话数据，并尝试直接生成下一步 Prompt。

## 第一版的可配置方式

当前工作流不是写死在页面里的，而是来自：

- `config/workflow-definitions/*.yaml`
- `prompts/*.md`

你后面如果想扩流程，第一版支持这套方式：

1. 新增一个工作流定义 YAML。
2. 在步骤里指定 prompt 模板、保存文件名、回填目标字段、生成前必填字段。
3. 在 prompt 中保持 `{{字段名}}` 占位符，并严格使用当前约定的输出包装格式。

这样页面会按工作流定义渲染步骤，后端会按配置保存和串联上下文。

## 这版保留了哪些可改项

以下内容都没有写死在仓库业务里，而是做成了输入字段：

- 输入文章类型
- 目标平台
- 平台预设规则
- 目标平台受众
- 平台写作风格
- 输出内容组成
- 长度要求
- 是否允许压缩
- 是否允许重组结构
- 是否允许在不改变原意的前提下换表达方式
- 是否允许补充原文没有的信息
- 必须保留的事实、观点、术语
- 额外约束和禁区

## 后续你可以怎么改

- 如果你后面要增加平台，只需要在 `config/platform-rules.yaml` 里补一组规则和别名。
- 如果你后面确定了固定输出格式，可以继续把 `templates/` 里的输入字段收敛成更少的必填项。
- 如果你后面要接入真实模型，可以在 `scripts/run_workflow.py` 的基础上继续加调用逻辑。
