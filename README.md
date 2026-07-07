# ai_workflow_kit

一个面向文章整理与多平台成稿场景的模板合并工作流仓库。

当前版本使用 `uv + Python` 自动把输入字段合并进 prompt 模板，并把结果写入 `outputs/`，不直接调用大模型 API。

## 这个仓库现在做什么

把一篇输入文章的要求整理清楚，并生成三个阶段的“已合并模板结果”，供你后续继续使用，同时严格保留原意相关约束。

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
├── pyproject.toml
├── prompts/
│   ├── article-structuring.md
│   ├── platform-copywriting.md
│   └── platform-copy-review.md
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

1. 先填写 `templates/article-to-platform-input.example.yaml`，把所有输入字段补齐。
2. 打开 `prompts/article-structuring.md`，整理原始文章。
3. 保存整理结果，作为后续平台成稿的中间材料。
4. 打开 `prompts/platform-copywriting.md`，把中间材料转换成目标平台文稿。
5. 检查标题、正文、结尾和标签是否符合本次平台要求。
6. 打开 `prompts/platform-copy-review.md`，对原文、整理材料和平台文稿做一轮对照检查。
7. 根据检查结果手动修正，直到文稿既符合平台需求，又没有偏离原意。

### 技术方案

适合先把输入字段和模板自动合并出来，再继续处理的场景。

1. 生成一份输入模板：

```bash
uv run python scripts/run_workflow.py init
```

默认会生成 `inputs/article-to-platform-input.yaml`。

2. 填写输入 YAML，把平台要求、长度、输出项和保护规则补齐。

3. 如有需要，可在输入 YAML 的中间字段中补充“整理后的文章材料”或“平台文稿”。

4. 运行模板合并：

```bash
uv run python scripts/run_workflow.py run --input inputs/article-to-platform-input.yaml
```

5. 脚本会自动完成三份 prompt 模板的字段合并：

- 整理原文 prompt 合并
- 平台成稿 prompt 合并
- 文稿复核 prompt 合并

6. 到 `outputs/<时间戳-平台名>/` 中查看合并后的结果文件。

## 你会得到什么

每次运行后，`outputs/` 下会生成一组文件：

- `01-article-structuring.merged.txt`
- `02-platform-copywriting.merged.txt`
- `03-platform-copy-review.merged.txt`
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

## 这版保留了哪些可改项

以下内容都没有写死在仓库业务里，而是做成了输入字段：

- 输入文章类型
- 目标平台
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

- 如果你后面确定了固定平台，可以直接复制 `prompts/platform-copywriting.md`，拆成多个平台专用 prompt。
- 如果你后面确定了固定输出格式，可以继续把 `templates/` 里的输入字段收敛成更少的必填项。
- 如果你后面要接入真实模型，可以在 `scripts/run_workflow.py` 的基础上继续加调用逻辑。
