# Eval Cases

这里存放评测用例（case）定义，用于端到端回归与对比。

建议结构（Phase 1 最小）：
- `inputs/`：章节输入快照（上一章/相关章节）、`continuation_req.json`、可选风格约束。
- `expected/`：期望点（must_include/must_not_include/continuity_constraints）、指标阈值、人工判分口径。
- `notes.md`：用例背景说明与人工注意事项。
