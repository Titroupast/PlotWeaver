# Day 5 工作总结

本次在 Day4 基础上新增“基础审校器”，生成结构化审校报告。

## 已完成内容

1. 审校器输出
   - 新增 reviewer 提示词（system + user）
   - 生成结构化审校报告 `review.json`

2. 审校输入
   - 本章正文
   - 人物设定摘要（来自 `characters.json`）
   - 世界观设定摘要（来自 `world_rules.md`）

3. 输出结构
   - 按章节目录输出：
     - `outputs/<novel_id>/chapters/<chapter_id>/review.json`

## 关键文件

- `app.py`（新增审校流程）
- `prompts/reviewer.txt`
- `prompts/reviewer_user.txt`

