# PlotWeaver Phase 1 Task Breakdown

更新时间：2026-03-15

本文档基于 [PHASE1_PLAN.md](./PHASE1_PLAN.md) 进一步拆分 Phase 1 首批任务，目标是让项目可以直接按工作线推进，而不是停留在抽象里程碑层。

---

## 1. 本次选用的 Skills

### 1.1 主 Skill

- `doc-coauthoring`
  - 作用：把 Phase 1 拆解成可执行的工作流、任务包和维护文档。

### 1.2 配套 Skill

- `vercel-react-best-practices`
  - 作用：约束 `apps/web` 任务线的实现方向，避免后期因为数据获取、组件边界和性能模式返工。

当前没有直接使用 `web-design-guidelines` 来拆任务，因为这份文档的重点是实施拆解，不是 UI 审核；但它应在 `apps/web` 进入验收前使用。

---

## 2. 任务拆分原则

Phase 1 的任务拆分遵守以下原则：

1. 先冻结共享契约，再推进 API 和 Web。
2. 先保住 `novel-agent-day6/`，再抽离 engine。
3. 先跑通 run 主链路，再补复杂 UI。
4. 高风险能力优先显式化，比如 gate、角色歧义、版本追溯。
5. 每条任务线都尽量能独立推进，但依赖关系必须明确。

---

## 3. 任务线总览

### 3.1 核心四条线

- `packages/shared`
- `packages/engine`
- `apps/api`
- `apps/web`

### 3.2 支撑任务线

- `infra`
- `docs`
- `eval_cases` / `eval_runs`
- 数据库与对象存储

---

## 4. `packages/shared` 首批任务

### 目标

把所有人都会依赖的数据契约、常量和接口类型先固定下来，避免 API、Web、Engine 各写一套。

### 首批任务

1. 建立 `packages/shared/` 基础目录
   - `schemas/`
   - `types/`
   - `constants/`
   - `openapi/` 或 `contracts/`

2. 固化核心 schema
   - `continuation_req`
   - `outline`
   - `chapter_meta`
   - `review`
   - `memory_gate`
   - `character_card`

3. 定义枚举和状态常量
   - run states
   - chapter status
   - chapter kind
   - character merge status

4. 补齐契约校验方式
   - Pydantic 模型
   - JSON Schema 导出或等价结构
   - 示例 payload

5. 定义 API 公共响应模型
   - `RunSummary`
   - `RunDetail`
   - `ArtifactSummary`
   - `ErrorResponse`

### 完成标准

- 四条主线都不再手写字段解释。
- 文档和代码使用同一批枚举与 schema。
- 至少有一份“正确示例 payload”可给前后端联调用。

### 依赖关系

- 这是最优先任务线。
- `apps/api`、`apps/web`、`packages/engine` 都依赖它。

---

## 5. `packages/engine` 首批任务

### 目标

把 Day6 里的生成逻辑抽离成可复用引擎，同时保证 CLI 仍然能跑。

### 首批任务

1. 设计 engine 目录结构
   - `planner/`
   - `writer/`
   - `reviewer/`
   - `memory/`
   - `prompts/`
   - `adapters/`
   - `models/`

2. 梳理 Day6 现有逻辑边界
   - CLI 参数解析和业务逻辑分离
   - prompt 加载与模型调用分离
   - 文件 IO 和核心步骤分离

3. 抽离 Planner 服务
   - 输入：上一章、上下文、requirement
   - 输出：`outline`

4. 抽离 Writer 服务
   - 输入：outline、memory context、requirement
   - 输出：`chapter.txt` + `chapter_meta`

5. 抽离 Reviewer 服务
   - 输出结构必须和 `packages/shared` 一致

6. 抽离 Memory Curator
   - 生成 delta
   - 输出 gate 输入候选

7. 保留 CLI 兼容层
   - `novel-agent-day6/app.py` 仍调用 engine
   - 行为不被服务化改坏

### 完成标准

- CLI 仍然可运行。
- API 后续可以直接调用 engine，不需要复制 Day6 逻辑。
- 每个步骤的输入输出都能被测试或校验。

### 依赖关系

- 依赖 `packages/shared` 的 schema。
- 被 `apps/api` 依赖。

---

## 6. `apps/api` 首批任务

### 目标

把 PlotWeaver 的主链路变成真正的服务：可创建 run、可推进状态、可保存产物、可追踪失败。

### 首批任务

1. 初始化 `apps/api/`
   - FastAPI
   - 配置加载
   - 路由分组
   - 健康检查接口

2. 建立 API 基础模块
   - `api/routes/`
   - `core/config.py`
   - `db/`
   - `services/`
   - `repositories/`
   - `schemas/`（如果不完全复用 shared 的 Python 包）

3. 实现 `POST /runs`
   - 校验 requirement schema
   - 创建 run 记录
   - 写入 `idempotency_key`
   - 返回 run 初始状态

4. 实现 `GET /runs/{run_id}`
   - 返回状态
   - 返回阶段产物引用
   - 返回错误信息和最近更新时间

5. 实现 run 状态推进服务
   - `DRAFT`
   - `OUTLINE_GENERATING`
   - `OUTLINE_READY`
   - `CHAPTER_GENERATING`
   - `CHAPTER_READY`
   - `REVIEW_GENERATING`
   - `REVIEW_READY`
   - `MEMORY_PENDING_GATE`

6. 实现 artifact 持久化
   - 保存 outline/review/gate 到 DB
   - 保存正文版本引用到 DB
   - 正文内容写 Storage

7. 实现人工 gate 接口
   - 通过
   - 拒绝
   - 编辑后通过

8. 实现角色歧义处理接口
   - 获取待确认角色项
   - 提交 merge decision

### 完成标准

- API 可以完整跑通一次 run。
- 失败时状态不丢失。
- 每个产物都能被查询和追溯。
- gate 和 merge decision 至少有最小接口。

### 依赖关系

- 依赖 `packages/shared` 和 `packages/engine`。
- 依赖数据库和 Storage 方案。

---

## 7. `apps/web` 首批任务

### 目标

交付最小但完整的 Web 工作台，而不是一套漂亮但空心的页面。

### 实施约束

本任务线应参考 `vercel-react-best-practices`：

- 先设计数据流，再设计组件。
- 尽量让服务端获取主数据，减少无意义客户端拉取。
- 不过早做复杂状态管理。
- 不让页面和接口字段耦合失控。

### 首批任务

1. 初始化 `apps/web/`
   - Next.js App Router
   - 路由分组
   - 基础 layout
   - API client 封装

2. 建立基础页面骨架
   - `/novels`
   - `/novels/[novelId]/chapters`
   - `/runs/[runId]`
   - `/admin/gates`（可后置）

3. 实现作品与章节列表
   - 先有可读性，再谈高级筛选
   - 明确章节状态和排序来源于 `chapter_meta`

4. 实现创建 run 的 requirement 表单
   - `chapter_goal`
   - `must_include`
   - `must_not_include`
   - `tone`
   - `continuity_constraints`
   - `target_length`

5. 实现 run 详情页
   - 状态展示
   - outline 展示
   - chapter 展示
   - review 展示
   - gate 展示

6. 实现错误和重试体验
   - 提交失败提示
   - 状态轮询失败提示
   - 运行失败后的操作建议

7. 预留人工 gate 后台入口
   - 审批面板
   - 待确认角色列表

### 完成标准

- 用户能不看文件目录就完成主要操作。
- Web 能看懂 run 发生了什么。
- requirement 表单不会让用户直接面对原始 JSON。

### 依赖关系

- 强依赖 `apps/api` 和 `packages/shared`。
- 页面深度依赖状态机与 artifact 结构是否稳定。

---

## 8. 数据库与 Storage 任务线

数据库详细方案见 [DB_PHASE1_PLAN.md](./DB_PHASE1_PLAN.md)。

### 首批任务

1. 选型确认
   - PostgreSQL
   - 建议 Supabase 托管
   - Storage 选 Supabase Storage 或 S3 兼容方案

2. 建最小表结构
   - `novels`
   - `chapters`
   - `chapter_versions`
   - `runs`
   - `artifacts`
   - `character_cards`
   - `memory_deltas`
   - `merge_decisions`

3. 确认“什么进数据库，什么进 Storage”
   - 正文不直接塞 `chapters`
   - DB 只放引用和元数据

4. 建立迁移策略
   - migration 目录
   - 初始建表脚本
   - 开发环境初始化说明

5. 为 API 准备 repository 层
   - novels repo
   - chapters repo
   - runs repo
   - artifacts repo
   - memory repo

### 完成标准

- API 能基于数据库而不是本地文件追踪 run。
- 正文和结构化元数据职责分离。
- 数据库结构能支撑 Phase 1 主链路。

---

## 9. `infra` 首批任务

### 目标

让 Phase 1 有最小可运行环境，而不是“本地能跑但别人接不起来”。

### 首批任务

1. 明确环境变量清单
2. 增加本地开发环境说明
3. 约定 API、Web、DB、Storage 的本地联调方式
4. 预留部署方式
   - Web
   - API
   - DB
   - Storage
5. 增加健康检查与基本日志策略

### 完成标准

- 新人按文档能在本地启动最小环境。
- 部署时不会临时猜环境变量和依赖。

---

## 10. `docs` / `eval` 首批任务

### `docs` 任务

1. 保持 `SPEC.md` 作为总规范
2. 保持 `PHASE1_PLAN.md` 作为里程碑计划
3. 新增数据库计划文档
4. 新增任务拆分文档
5. 更新 `docs/README.md` 导航

### `eval_cases` / `eval_runs` 任务

1. 选 10 到 20 个代表性 case
2. 每个 case 包含：
   - 上一章摘要
   - requirement
   - 期望点
   - 禁止点
3. 记录回归结果
4. 形成最小回归基线

### 完成标准

- 文档可导航、可维护。
- 每次主链路改动都有固定 case 能跑。

---

## 11. 建议的首批任务顺序

建议实际开工顺序如下：

1. `packages/shared`
2. `packages/engine`
3. 数据库与 Storage 基础结构
4. `apps/api`
5. `apps/web`
6. gate / merge decision
7. infra / eval / docs 收尾

如果资源有限，最低并行度建议：

- 一条人线做 `shared + engine`
- 一条人线做 `database + api`
- 一条人线在 API 结构稳定后进入 `web`

---

## 12. 维护建议

为了让项目后面不失控，建议从 Phase 1 开始就坚持：

- 所有新接口先更新契约，再写代码。
- 所有结构化产物都给示例和校验。
- 所有高风险自动化都保留人工入口。
- 所有重大改动都更新 `docs/` 导航。
- 所有 run 相关功能都围绕可追溯性设计。

这份文档的目的，是让 Phase 1 从“一个大目标”变成“每条线今天就能开始做什么”。
