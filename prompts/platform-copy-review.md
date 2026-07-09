---
name: platform-copy-review
version: 1.0
use_case: 在交付前检查平台文稿是否偏离原意
inputs:
  - source_article
  - structured_article_notes
  - target_platform
  - platform_rule_name
  - platform_rule_pack
  - platform_draft
  - facts_that_must_be_retained
  - terms_not_to_change
  - new_information_allowed
  - review_focus
outputs:
  - meaning_deviation_check
  - missing_facts
  - unsupported_additions
  - revision_advice
  - approval_recommendation
---

# 用途

在最终交付前，检查平台文稿有没有偏离原意、遗漏关键事实或擅自新增信息。

# Prompt 使用方式

非技术方案：
把下面的 `text` 代码块复制到 AI 工具中，手动替换所有 `{{...}}` 占位符后再运行。

技术方案：
下面的 `text` 代码块会由脚本自动读取并自动替换占位符，合并结果写入 `outputs/`。

```text
你是一名内容质检助手。

请对比原始文章、整理后的材料和平台文稿，重点检查是否存在原意偏移。

输入信息如下：

原始文章：
{{source_article}}

整理后的文章材料：
{{structured_article_notes}}

目标平台：
{{target_platform}}

命中的平台预设规则：
{{platform_rule_pack}}

平台文稿：
{{platform_draft}}

必须保留的事实：
{{facts_that_must_be_retained}}

不可改动的术语：
{{terms_not_to_change}}

是否允许补充原文没有的信息：
{{new_information_allowed}}

本轮审查重点：
{{review_focus}}

请按以下结构输出：
1. 原意偏移检查
2. 缺失事实
3. 无依据新增内容
4. 修改建议
5. 审核建议：通过 / 修改后再审

输出要求：
- 优先指出会改变原意的问题。
- 同时检查文稿是否明显违背当前平台预设规则，尤其是篇幅、结构、开头方式和整体语气。
- 如果发现新增信息，要明确标出对应句子或片段。
- 修改建议要具体到可直接回填。
```

# 质量检查清单

- 是否准确指出了原意偏移处？
- 是否识别出遗漏的关键事实？
- 是否识别出无依据新增内容？
- 建议是否足够具体，能直接用于返修？
