本轮我按 `create-implementation-plan` + `software-architecture-design` + `validate-implementation-plan` 的思路给你整理了“只出方案不写代码”的落地版。

**一、先定好要用的 Skills**
建议分两类：本地现有优先 + 外部补充少量高价值。

1. 本地现有（直接可用）
- `create-implementation-plan`
- `validate-implementation-plan`
- `software-architecture-design`
- `ai-agent-development`
- `vercel-react-best-practices`
- `web-design-guidelines`
- `architecture-documentation`
- `deploy-to-vercel`

2. 建议补充安装（你当前阶段最匹配）
- `npx skills add wshobson/agents@nextjs-app-router-patterns`
- `npx skills add supabase/agent-skills@supabase-postgres-best-practices`
- `npx skills add aj-geddes/useful-ai-prompts@fastapi-development`
- `npx skills add speakeasy-api/skills@extract-openapi-from-code`

**二、数据库/后端需提前确定的库（建议清单）**
目标是 Day6 Python 管线平滑迁移到 FastAPI + Next.js，全程契约优先。

1. 后端核心
- `fastapi`
- `uvicorn[standard]`
- `pydantic`（含 settings）
- `sqlalchemy`（2.x）
- `alembic`
- `psycopg[binary]`（或 async 驱动 `asyncpg`）
- `httpx`（服务内调用/测试）

2. 认证与安全
- `python-jose[cryptography]` 或 `PyJWT`
- `passlib[bcrypt]`
- 若用 Supabase Auth：后端校验 JWT（JWK 缓存 + audience/issuer 校验）

3. 异步任务与流式输出（可选但推荐预留）
- `redis`
- `rq` 或 `celery`（二选一）
- SSE：`sse-starlette`（或原生 StreamingResponse）

4. 数据契约与质量
- `jsonschema`（契约校验）
- `orjson`（高性能 JSON）
- `openapi` 由 FastAPI 原生生成，必要时配合上面的 extract skill 做一致性检查

5. 测试与可观测性
- `pytest`
- `pytest-asyncio`
- `respx`（mock httpx）
- `opentelemetry-sdk` + `opentelemetry-instrumentation-fastapi`
- `structlog`（结构化日志）

**三、Task 拆分（每块用什么 Skill + 提示词）**
下面每个 task 都是“可独立推进”的最小单元。

1. Task A：冻结数据契约（最优先）
- 目标：锁定 `outline.json/review.json/characters.json/chapter_meta.json/memory_gate.json` 的 schema 与版本策略
- Skills：`create-implementation-plan` + `validate-implementation-plan`
- 提示词模板：  
`基于 Day6 现有输出，生成“契约冻结计划”。要求：逐文件定义 Pydantic 模型与 JSON Schema，明确必填字段、版本号、向后兼容策略、变更流程；输出必须包含任务列表、验收标准、风险与回滚。`

2. Task B：FastAPI 骨架与分层
- 目标：搭建 API 工程骨架（router/service/repository/schema）
- Skills：`software-architecture-design` + `fastapi-development`
- 提示词模板：  
`为 PlotWeaver 设计 FastAPI 分层架构，约束：契约优先、可替换存储、支持长任务。请给出目录结构、模块边界、依赖注入方式、错误码规范、OpenAPI 分组策略，以及“暂不实现内容”。`

3. Task C：数据库建模与迁移策略
- 目标：定义 Postgres 模型（project/chapter/run/memory/character/requirement）与迁移路径
- Skills：`supabase-postgres-best-practices` + `software-architecture-design`
- 提示词模板：  
`针对 PlotWeaver 设计 PostgreSQL Schema 与 Alembic 迁移方案，要求：支持多租户/RLS、章节版本历史、软删除、审计字段、索引策略；输出 ERD 说明、迁移顺序、数据回填方案和性能风险。`

4. Task D：Agent 编排服务化
- 目标：把 Planner/Writer/Reviewer/Memory Curator 变成可编排后端任务
- Skills：`ai-agent-development`
- 提示词模板：  
`将 Day6 CLI 管线拆分为后端可编排任务流。要求：定义输入输出契约、幂等键、失败重试、断点续跑、人工复核节点；输出状态机与任务队列交互设计，不写具体代码。`

5. Task E：Next.js 前端迁移
- 目标：实现项目管理、续写配置、生成过程、结果审阅的 App Router 信息架构
- Skills：`nextjs-app-router-patterns` + `vercel-react-best-practices`
- 提示词模板：  
`为 PlotWeaver 设计 Next.js App Router 前端架构。要求：路由树、数据获取策略、服务端与客户端组件边界、表单与流式状态管理、错误与加载体验、移动端适配基线。`

6. Task F：实时输出与长任务体验
- 目标：前后端打通生成进度流（SSE）
- Skills：`software-architecture-design`
- 提示词模板：  
`设计 PlotWeaver 的实时进度通道（优先 SSE）。要求：事件类型定义、重连策略、顺序保证、前端状态机、超时和降级方案；列出可观测指标与告警阈值。`

7. Task G：测试与验收门禁
- 目标：建立契约测试、API 集成测试、端到端关键路径测试
- Skills：`create-implementation-plan` + `validate-implementation-plan`
- 提示词模板：  
`生成 PlotWeaver 迁移阶段测试门禁方案。要求：契约测试优先、关键 API 集成测试、最小 E2E 回归路径、CI 触发条件、失败阻断规则、发布前检查清单。`

8. Task H：部署与运行手册
- 目标：前端 Vercel、后端容器化部署、环境变量与密钥规范
- Skills：`deploy-to-vercel` + `architecture-documentation`
- 提示词模板：  
`输出 PlotWeaver 部署蓝图：Next.js on Vercel + FastAPI 独立服务 + Postgres/Supabase。要求：环境分层(dev/staging/prod)、密钥管理、回滚流程、成本监控、值班告警与运行手册目录。`

**四、执行顺序建议（避免返工）**
1. A 契约冻结  
2. C 数据库建模  
3. B 后端骨架  
4. D Agent 编排  
5. E 前端迁移  
6. F 实时能力  
7. G 测试门禁  
8. H 部署上线

**五、此阶段明确“先不做”**
- 不先做移动端 App（仅预留 API）
- 不先做复杂微服务拆分（先模块化单体 + 清晰边界）
- 不先做“全自动人物合并”，保留人工确认入口（与你 AGENTS.md 约束一致）

如果你愿意，我下一步可以直接给你一份 `PHASE1 -> PHASE2` 的“周计划版任务板”（每周目标、输入、输出、验收标准、风险）。