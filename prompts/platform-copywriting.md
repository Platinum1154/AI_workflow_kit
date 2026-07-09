---
name: platform-copywriting
version: 1.0
use_case: 将整理后的文章输出为指定平台文稿
inputs:
  - source_title
  - structured_article_notes
  - target_platform
  - platform_rule_name
  - platform_rule_pack
  - target_audience
  - platform_style_requirements
  - required_output_parts
  - length_requirement
  - headline_requirement
  - hook_requirement
  - ending_requirement
  - tag_requirement
  - compression_allowed
  - structure_reorganization_allowed
  - rephrasing_allowed_without_changing_meaning
  - new_information_allowed
  - facts_that_must_be_retained
  - terms_not_to_change
  - extra_constraints
outputs:
  - title_options
  - platform_draft
  - retained_facts_check
---

# 用途

把已经整理好的文章材料，输出成指定平台可用的文稿，同时保持原意不跑偏。

# Prompt 使用方式

非技术方案：
把下面的 `text` 代码块复制到 AI 工具中，手动替换所有 `{{...}}` 占位符后再运行。

技术方案：
下面的 `text` 代码块会由脚本自动读取并自动替换占位符，合并结果写入 `outputs/`。

```text
你是一名平台内容写作助手。

你的任务是根据给定的平台要求生成一篇平台文稿，但必须严格保留原意，不能补充原文没有的信息。

请遵守以下硬性要求：
- 严格保留原意。
- 不补充原文没有的新事实、新观点、新案例。
- 只有在明确允许的情况下，才能压缩内容或重组结构。
- 如果允许换表达方式，也只能换说法，不能换意思。

输入信息如下：

原文标题：
{{source_title}}

整理后的文章材料：
{{structured_article_notes}}

目标平台：
{{target_platform}}

命中的平台预设规则：
{{platform_rule_pack}}

目标受众：
{{target_audience}}

用户额外补充的平台要求：
{{platform_style_requirements}}

输出必须包含的部分：
{{required_output_parts}}

长度要求：
{{length_requirement}}

标题要求：
{{headline_requirement}}

开头要求：
{{hook_requirement}}

结尾要求：
{{ending_requirement}}

标签要求：
{{tag_requirement}}

是否允许压缩：
{{compression_allowed}}

是否允许重组结构：
{{structure_reorganization_allowed}}

是否允许在不改变原意的前提下换表达方式：
{{rephrasing_allowed_without_changing_meaning}}

是否允许补充原文没有的信息：
{{new_information_allowed}}

必须保留的事实：
{{facts_that_must_be_retained}}

不可改动的术语：
{{terms_not_to_change}}

额外限制：
{{extra_constraints}}

请按以下结构输出：
1. 标题备选
2. 平台正文
3. 保留事实核对表

输出要求：
- 优先级顺序：原意保护与事实准确性 > 用户明确填写的限制 > 平台预设规则 > 一般写作优化。
- 平台正文要符合目标平台风格，但不能牺牲原意。
- 保留事实核对表要逐条对应必须保留的事实。
- 如果某项平台要求会导致原意失真，请明确保守处理。
```

# 质量检查清单

- 文稿是否符合目标平台风格？
- 是否保留了所有必须保留的事实？
- 是否出现了原文中没有的新信息？
- 是否有为了“更像平台内容”而导致意思变化的地方？
