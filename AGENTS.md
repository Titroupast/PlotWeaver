# Agent 指南（PlotWeaver）

本仓库以 `novel-agent-day6/` 为当前参考实现（Day1–Day5 历史原型已清理；如需回看请查 Git 历史）。

## 关键文档

- 产品/技术规格：`SPEC.md`
- 项目结构规划：`PROJECT_STRUCTURE.md`
- Day6 原型使用说明：`novel-agent-day6/USAGE.md`

## 事实来源与范围

- 需要描述“项目现在怎么工作”的内容时，以 `novel-agent-day6/` 为准。
- 优先保证 Day6 CLI 可用，再逐步服务化到全栈。

## 最终形态（全栈 + 部署 + 移动端）

PlotWeaver 的目标是做成可部署的全栈产品：网页端优先，后续可扩展到移动 App。

推荐技术栈（与当前 Day6 Python 管线最匹配的演进路径）：

- Web：Next.js（App Router）+ TypeScript
- 后端 API：FastAPI（Python）+ OpenAPI（接口文档与类型契约）
- 数据库：PostgreSQL（建议 Supabase 托管 + RLS）
- Storage：对象存储保存章节/草稿/长日志（DB 只存元数据与引用）
- 长任务（可选）：Redis + RQ/Celery
- 实时输出（可选）：SSE 或 WebSocket
- 移动端（后续）：Expo（React Native），复用同一套 API

## 数据契约与 Schema 规则

- `outline.json`、`review.json`、`characters.json` 等结构化输出视为“契约”。一旦变更：必须同步更新 `SPEC.md`。
- 优先把契约固化为显式 schema（Pydantic / JSON Schema），再让更多功能依赖它。

## 编写与编辑规范

- 文档统一 UTF-8 编码。
- 避免大段重写；优先增量修改，确保 `SPEC.md` 与代码/行为一致。

## Agent 角色与 I/O（对齐 `SPEC.md`）

- Planner：输入＝上一章片段 + 三层记忆提示层片段 + 结构化续写要求（`continuation_req.json`）；输出＝`outline.json`。
- Writer：输入＝`outline.json` + 记忆上下文 + 续写要求；输出＝`chapter.txt`（仅正文）+ `chapter_meta.json`（标题/类型/摘要/排序/状态）。
- Reviewer：输入＝正文 + 元数据 + 续写要求；输出＝`review.json`（并在建议中显式检查 must_include/must_not_include/continuity_constraints）。
- Memory Curator：输入＝正文 + 主记忆；输出＝`memory delta`（候选增量记忆）+ `memory_gate.json`（闸门建议）。
- Fact Checker（可选）：输入＝事实层候选 + 引用线索；输出＝冲突列表/需要人工确认的项。
- Rewriter（按需）：输入＝review 结论 + requirement；输出＝新 run 的重写版本（保留历史版本）。

## 常见坑（必须避免）

- 标题来源：不要把“正文第一行”当作唯一标题来源；标题应来自结构化元信息（例如 `chapter_meta`）或 `title.txt`。
- 人物合并：不要只用 `name` 作为唯一主键；需要稳定 `character_id` + `aliases`，并为同名/化名提供人工确认入口。
