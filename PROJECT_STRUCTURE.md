# 项目结构规划（以 Day6 为起点）

目标：以 `novel-agent-day6/` 的生成闭环为起点，逐步演进为可部署的全栈项目（Web 优先，后续移动端）。

## 当前事实来源

- 生成管线参考实现：`novel-agent-day6/`

> Day1–Day5 历史原型已从工作区清理；如需回看通过 Git 历史找回。

## 推荐目录布局（落地全栈）

- `apps/web/`：Next.js Web 前端（编辑器、章节管理、生成/审校面板、人工介入后台 Admin Console）
- `apps/api/`：FastAPI 后端（REST + OpenAPI；长任务可扩展 SSE/WebSocket）
- `packages/shared/`：共享契约（JSON Schema、OpenAPI 类型、公共常量）
- `packages/engine/`：（后续）从 `novel-agent-day6/` 抽离出的 Python 生成引擎
- `infra/`：部署/环境说明（Vercel、Supabase、worker 等）
- `docs/`：补充文档（`SPEC.md` 仍保持在仓库根目录）


## 评测与回归（建议）

- `eval_cases/`：评测用例集合（稳定输入与期望点/约束）。
- `eval_runs/`：每次回归的结果快照与对比报告（用于定位退化）。
- `memory_updates/`：待审批的 memory delta 与闸门结果的文件化兼容落点（Phase 1 可选；最终应落库）。
- `merge_decisions/`：同名/化名冲突的人工合并决策记录（Phase 1 可选；最终应落库）。

## 迁移策略（建议）

1. 先保证 `novel-agent-day6/` 仍可独立运行（CLI 不断）。
2. 在 `apps/api/` 里把 Day6 逻辑包一层 API（先跑通单条“生成下一章”）。
3. 再抽离核心逻辑到 `packages/engine/`，让 CLI 和 API 都依赖同一套引擎。
4. 最后再补全用户体系、存储（Storage）、数据库（Postgres）与队列（可选）。
