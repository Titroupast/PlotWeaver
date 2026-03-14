# Eval Runs

这里存放每次评测运行（eval run）的输出与汇总，便于回归对比与质量闸门。

建议内容（Phase 1 最小）：
- `run_manifest.json`：本次评测使用的模型/提示词版本/代码版本/时间戳。
- `results.json`：逐 case 的指标结果与通过/失败原因。
- `artifacts/`：必要的产物快照（outline/chapter/review/memory_delta/gate）。
