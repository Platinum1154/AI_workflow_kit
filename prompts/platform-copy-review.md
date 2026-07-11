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

在最终交付前，检查平台文稿有没有偏离原意、遗漏关键事实或擅自新增信息，并给出清晰可执行的审查报告，供下一步最终写作使用。

# Prompt 使用方式

非技术方案：
把下面的 `text` 代码块复制到 AI 工具中，手动替换所有 `{{...}}` 占位符后再运行。

技术方案：
下面的 `text` 代码块会由脚本自动读取并自动替换占位符，合并结果写入 `outputs/`。

```text
你是一名内容质检助手。

请对比原始文章、整理后的材料和平台文稿，重点检查是否存在原意偏移，并输出一份可以直接交给最终写作助手使用的审查报告。

你现在不是在“阅读一个 Prompt 文件”或“解释这份 Markdown 是什么”，而是在直接执行其中的任务。

绝对禁止出现以下类型的过程性废话：
- “我已阅读这份 Markdown”
- “从目前看到的内容来看”
- “如果你的目标是……我可以继续处理”
- “我注意到后半部分应该还有……”
- “继续”
- 任何要求用户再次确认、继续、补发后半部分的句子

默认判断：你已经拿到了完成本任务所需的全部输入，必须直接完成任务并一次性输出审查报告。

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

请按以下结构输出审查报告：
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
- 不要在本步骤直接重写终稿；本步骤只负责给出高质量审查报告。
- 修改建议要让下一步最终写作助手能直接据此生成终稿。
- `PRIMARY_CONTENT_START` 和 `PRIMARY_CONTENT_END` 之间只放正式结果，不要重复包装说明。
- `PRIMARY_CONTENT_START` 和 `PRIMARY_CONTENT_END` 之间必须放完整审查报告，不要放终稿。
- `STRUCTURED_JSON` 必须是合法 JSON。
- 你的输出第一行必须直接是 `<<<AI_WORKFLOW_OUTPUT_START>>>`，不能在前面增加任何说明文字。
- 除了规定的包装格式外，禁止输出任何额外内容。

最终输出时，必须严格使用下面的包装格式，不能在包装格式前后添加任何说明、寒暄、代码围栏或备注：

<<<AI_WORKFLOW_OUTPUT_START>>>
step_id: platform-copy-review
status: ok
primary_target: review.latest_report
<<<PRIMARY_CONTENT_START>>>
[把审查报告完整输出在这里，按“原意偏移检查 / 缺失事实 / 无依据新增内容 / 修改建议 / 审核建议”结构书写]
<<<PRIMARY_CONTENT_END>>>
<<<STRUCTURED_JSON_START>>>
{
  "step_id": "platform-copy-review",
  "ready_for_next_step": true,
  "summary": "用一句话概括本步结果",
  "approval_recommendation": "通过或修改后通过"
}
<<<STRUCTURED_JSON_END>>>
<<<AI_WORKFLOW_OUTPUT_END>>>
```

# 质量检查清单

- 是否准确指出了原意偏移处？
- 是否识别出遗漏的关键事实？
- 是否识别出无依据新增内容？
- 建议是否足够具体，能直接用于返修？
- 是否已经为下一步最终写作提供了足够明确的修改依据？
