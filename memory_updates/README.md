# Memory Updates

这里存放“增量记忆”（memory delta）与闸门（gate）相关的文件化落点，便于人工审批与审计。

建议内容（Phase 1 最小）：
- `*_memory_delta.json`：本次 run 产生的增量记忆（含来源引用）。
- `*_memory_gate.json`：自动闸门评估结果与 issues 列表（最终以人工为准）。
- `characters_pending_review.json`：角色合并存在歧义时的待人工处理清单。
