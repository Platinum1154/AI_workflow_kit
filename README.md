# ai_workflow_kit

一个面向手动使用场景的文章整理与多平台成稿模板仓库。

当前版本只保留最必要的结构，重点不是自动化调用，而是先把这件事做成一个清晰、可复制、可继续改 prompt 的工作流骨架。

## 这个仓库现在做什么

把一篇输入文章整理清楚，再按照指定平台要求产出对应文稿，同时严格保留原意。

## 当前原则

- 严格保留原意
- 不补充原文没有的信息
- 平台、风格、长度、输出项等全部作为输入字段
- Prompt 先保持通用，后续可按你的实际使用继续细化

## 最小目录结构

```text
ai_workflow_kit/
├── README.md
├── .gitignore
├── prompts/
│   ├── article-structuring.md
│   ├── platform-copywriting.md
│   └── platform-copy-review.md
├── workflows/
│   └── article-to-platform-workflow.md
└── templates/
    └── article-to-platform-input.example.yaml
```

## 怎么用

1. 准备原始文章和平台要求。
2. 先参考 `templates/article-to-platform-input.example.yaml` 填输入字段。
3. 打开 `prompts/article-structuring.md`，先把原文整理成结构化信息。
4. 再打开 `prompts/platform-copywriting.md`，生成指定平台文稿。
5. 最后用 `prompts/platform-copy-review.md` 做一轮人工复核前的 AI 自检。

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
- 如果你后面要做自动化，再补脚本、配置文件和输出目录即可。
