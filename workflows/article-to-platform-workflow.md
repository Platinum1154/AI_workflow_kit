# 目标

把输入文章先整理成稳定的结构化材料，再输出为指定平台文稿，同时严格保留原意。

# 必需输入

- 原始文章标题
- 原始文章正文
- 文章类型
- 原文语言
- 目标平台
- 目标受众
- 平台写作风格要求
- 输出必须包含的部分
- 长度要求
- 标题要求
- 开头要求
- 结尾要求
- 标签要求
- 是否允许压缩
- 是否允许重组结构
- 是否允许在不改变原意的前提下换表达方式
- 是否允许补充原文没有的信息
- 必须保留的事实
- 不可改动的术语
- 额外限制

# 非技术方案步骤

1. 先填写 `templates/article-to-platform-input.example.yaml`，通常至少只需要补 `source_article`，其他字段按需补充。
2. 打开 `prompts/article-structuring.md`，整理原始文章。
3. 保存整理结果，作为后续平台成稿的中间材料。
4. 打开 `prompts/platform-copywriting.md`，把中间材料转换成目标平台文稿。
5. 检查标题、正文、结尾和标签是否符合本次平台要求。
6. 打开 `prompts/platform-copy-review.md`，对原文、整理材料和平台文稿做一轮对照检查。
7. 根据检查结果手动修正，直到文稿既符合平台需求，又没有偏离原意。

# 技术方案步骤

1. 运行 `uv sync` 安装依赖。
2. 运行 `uv run python scripts/run_workflow.py init` 生成输入模板。
3. 填写输入 YAML。通常至少填原文和 `target_platform`；脚本会自动注入该平台的预设规则，其他要求按需补充。
4. 如有需要，可在输入 YAML 的中间字段中补充“整理后的文章材料”或“平台文稿”。
5. 运行 `uv run python scripts/run_workflow.py run --input <你的输入文件>`。
6. 脚本会自动完成三份 prompt 模板的字段合并。
7. 到 `outputs/` 中查看合并后的结果文件。

# 使用的 prompts

- `prompts/article-structuring.md`
- `prompts/platform-copywriting.md`
- `prompts/platform-copy-review.md`
- `scripts/run_workflow.py`

# 预期输出

非技术方案：
- 1 份整理后的文章结构化材料
- 1 份指定平台文稿
- 1 份复核后的修改建议

技术方案：
- 1 份原文整理阶段的合并 prompt
- 1 份平台成稿阶段的合并 prompt
- 1 份复核阶段的合并 prompt

# 人工审核清单

非技术方案：
- 文稿是否严格保留原意？
- 是否出现原文没有的新事实、新观点或新案例？
- 是否遗漏了必须保留的事实？
- 平台风格是否符合要求，但没有为了风格牺牲内容准确性？
- 标题、开头、结尾、标签等是否满足本轮输入要求？

技术方案：
- 输入字段是否已经填完整？
- 三个阶段的合并结果是否都成功生成？
- 中间字段是否需要后续手动补充？
- 平台预设规则、用户补充要求和保护规则是否都正确进入模板？
