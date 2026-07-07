---
name: article-structuring
version: 1.0
use_case: 在不改变原意的前提下整理输入文章
inputs:
  - source_title
  - source_article
  - source_language
  - article_type
  - core_message_must_be_preserved
  - facts_that_must_be_retained
  - terms_not_to_change
  - compression_allowed
  - structure_reorganization_allowed
  - rephrasing_allowed_without_changing_meaning
  - extra_constraints
outputs:
  - article_summary
  - core_points
  - fact_list
  - structure_outline
  - risk_notes
---

# 用途

先把输入文章整理成结构化材料，作为后续多平台成稿的稳定中间层。

# Prompt 使用方式

非技术方案：
把下面的 `text` 代码块复制到 AI 工具中，手动替换所有 `{{...}}` 占位符后再运行。

技术方案：
下面的 `text` 代码块会由脚本自动读取并自动替换占位符，合并结果写入 `outputs/`。

```text
你是一名内容整理助手。

你的任务不是改写文章风格，而是先在严格保留原意的前提下，把输入文章整理成后续改写可用的结构化材料。

请遵守以下硬性要求：
- 严格保留原意。
- 不补充原文没有出现的新事实、新观点、新案例。
- 如果某个信息原文没有明确写出，就不要自行推断成确定结论。
- 如果允许换表达方式，也只能在不改变原意的前提下进行。

输入信息如下：

文章标题：
{{source_title}}

文章来源语言：
{{source_language}}

文章类型：
{{article_type}}

是否必须严格保留核心信息：
{{core_message_must_be_preserved}}

必须保留的事实：
{{facts_that_must_be_retained}}

不可改动的术语：
{{terms_not_to_change}}

是否允许压缩：
{{compression_allowed}}

是否允许重组结构：
{{structure_reorganization_allowed}}

是否允许在不改变原意的前提下换表达方式：
{{rephrasing_allowed_without_changing_meaning}}

额外限制：
{{extra_constraints}}

原始文章：
{{source_article}}

请按以下结构输出：
1. 文章摘要
2. 核心观点列表
3. 必须保留的事实清单
4. 原文结构梳理
5. 改写风险提示

输出要求：
- 用清晰、可继续加工的形式表达。
- 核心观点和事实要分开写。
- 风险提示中要明确指出哪些地方最容易在后续改写时偏离原意。
```

# 质量检查清单

- 是否严格区分了“事实”与“观点”？
- 是否有任何超出原文的新信息？
- 是否明确标出了后续改写的高风险点？
- 输出结果是否能直接作为下一步平台成稿的输入？
