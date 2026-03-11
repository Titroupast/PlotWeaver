# Day 6 工作总结

本次在 Day5 基础上新增“增量记忆更新 + 质量闸门”。

## 已完成内容

1. 增量记忆生成
   - 基于**新章节**生成三类 delta：
     - `characters_delta.json`
     - `world_rules_delta.md`
     - `story_so_far_delta.md`
   - 保存到 `inputs/<novel_id>/memory/updates/`

2. 质量闸门
   - 使用 Day5 的审校结果 `review.json` 进行阈值判断
   - 输出 `memory_gate.json`（pass + issues）
   - 通过后自动合并到主记忆文件

3. 合并策略（MVP）
   - characters：按 name 合并，列表去重、缺失字段补齐
   - world_rules / story_so_far：新增条目去重追加

## 关键文件

- `app.py`（新增增量更新与闸门逻辑）
- `tools.py`（新增 delta 构建工具）
- `prompts/memory_*_delta.txt`（delta 提示词）

