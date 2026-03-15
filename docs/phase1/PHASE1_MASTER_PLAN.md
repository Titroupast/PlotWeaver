# PlotWeaver Phase 1 总计划

日期：2026-03-15

这份文档是 PlotWeaver 的 Phase 1 统一主计划。以后优先看这一份，不必在计划、任务拆分、数据库方案之间来回切换。它把 Phase 1 的目标、范围、工作流拆分、数据库方案、里程碑、风险、验收标准和首批实施任务集中到同一个入口里，方便维护和后续开工。

## 1. Phase 1 要解决什么

Phase 1 的目标不是一次性做成完整商业产品，而是把 `novel-agent-day6/` 已经可用的能力，稳定迁移为一个最小可运行的全栈系统，让它具备“可追踪、可查看、可维护”的产品底座。

到 Phase 1 结束时，我们应该能够：

- 创建一本小说项目
- 为目标章节提交结构化续写要求
- 触发一次完整的续写 run
- 持久化保存 run 状态、章节版本和结构化产物
- 在 Web 界面查看 outline、chapter、review 和 memory gate 结果
- 为后续的重写、人物合并、评测和移动端扩展保留清晰边界

一句话概括：Phase 1 要把 Day6 的脚本工作流变成一个真正可演进的产品基础。

## 2. 本阶段范围

### In Scope

- 继续以 `novel-agent-day6/` 为事实基线
- 冻结核心结构化契约
- 建立最小数据库与 Storage 方案
- 提供最小可用的 FastAPI 后端
- 提供最小可用的 Next.js Web 前端
- 跑通 Planner -> Writer -> Reviewer -> Memory Curator 的完整链路
- 持久化保存 run 状态、artifacts 和 chapter versions

### Out of Scope

- 复杂的多租户权限系统
- 移动端 App
- 复杂的分布式异步调度
- 向量数据库和高级检索平台化
- 完全无人介入的人物自动合并
- 大规模性能优化

## 3. 本次整合采用的思路

这份统一计划主要落实了以下几类思路：

- `doc-coauthoring`：把分散文档收拢成一个可读、可维护的主入口
- `product-requirements`：明确目标、范围和成功标准
- `software-architecture-design`：明确 Web、API、Engine、数据库和 Storage 的边界
- `ai-agent-development`：明确 Planner、Writer、Reviewer、Memory Curator 的职责和输入输出
- `create-implementation-plan`：把计划拆成可执行的工作流和里程碑
- `validate-implementation-plan`：检查依赖顺序、风险点和落地闭环

## 4. 系统总体形态

推荐的 Phase 1 结构如下：

- `packages/shared`：schema、枚举、DTO 和示例数据
- `packages/engine`：Day6 工作流适配层和领域服务
- `apps/api`：FastAPI 服务，对外暴露 runs、chapters 和 artifacts
- `apps/web`：Next.js 界面，用于提交 requirement 和查看 run 结果
- `PostgreSQL`：保存结构化元数据、run 状态和 JSON artifacts
- `Storage`：保存章节正文、草稿和长日志

最核心的一条原则是：数据库负责“结构化状态和索引”，Storage 负责“长文本内容”。

## 5. 主要数据流

Phase 1 需要先稳定下面这条主链路：

1. 用户在 Web 中提交 continuation requirement
2. API 创建一条 run 记录
3. Engine 读取上一章上下文、记忆层和 requirement 数据
4. Planner 生成 `outline.json`
5. Writer 生成 `chapter.txt` 和 `chapter_meta.json`
6. Reviewer 生成 `review.json`
7. Memory Curator 生成 `memory_gate.json` 和候选 memory delta
8. API 把结构化产物写入数据库，把章节正文写入 Storage
9. Web 展示本次 run 的状态和产物

各角色职责如下：

- Planner：根据 requirement 和记忆上下文生成结构化大纲
- Writer：根据大纲和上下文生成正文与章节元信息
- Reviewer：检查质量、连续性和 requirement 满足情况
- Memory Curator：提出记忆更新建议和 gate 决策建议

## 6. 模块拆分与详细计划

### 6.1 `packages/shared`

这是最先开工的一条线，因为其他层都会依赖它。

#### 目标

- 冻结核心契约
- 避免前后端重复维护字段定义
- 为 API、数据库和 Engine 提供统一语言

#### P0

- 建立 `schemas/`、`constants/`、`examples/`
- 定义 `continuation_req` schema
- 定义 `outline` schema
- 定义 `chapter_meta` schema
- 定义 `review` schema
- 定义 `memory_gate` schema
- 定义 run state、chapter status、chapter kind 等枚举
- 为每个 schema 提供最小示例 payload

#### P1

- 增加 `character_card` schema
- 产出可给 API 复用的 DTO 定义
- 增加 schema 版本策略
- 补一份契约变更规则，约束后续升级方式

#### 完成标准

- API、Engine、Web 都引用同一套契约来源
- `SPEC.md` 提到的核心结构化文件都有对应 schema
- 后续字段修改有唯一入口，不会多处不一致

### 6.2 `packages/engine`

这一层负责把 Day6 脚本能力整理成可复用服务。

#### 目标

- 保留 Day6 已验证可用的能力
- 把零散脚本行为收敛成明确的领域模块
- 让 API 不直接依赖脚本内部细节

#### P0

- 盘点 Day6 当前输入输出契约
- 建立 `planner/`、`writer/`、`reviewer/`、`memory/` 等模块
- 为每个 agent 定义稳定入口函数
- 为每个 agent 定义统一输入输出 DTO
- 定义一次 run 的 orchestration 流程
- 保留 Day6 CLI 作为回归对照路径

#### P1

- 增加错误分类和失败类型
- 统一日志输出结构
- 统一 prompt 模板加载方式
- 为 Rewriter 和 Fact Checker 预留扩展接口

#### 完成标准

- API 只调用 engine service，不需要理解 Day6 脚本细节
- 相同输入能稳定得到结构化输出
- 任一 agent 失败时，run 状态仍然可追踪

### 6.3 数据库与 Storage

这一部分最容易让人发怵，所以 Phase 1 只做最小可用。

#### 设计原则

- PostgreSQL 保存结构化元数据、状态和 JSON artifacts
- Storage 保存章节正文、草稿和长日志
- 整个系统以 run 为中心组织，而不是靠扫描目录猜状态

#### 为什么这样拆分

PlotWeaver 不只是内容展示系统，它真正复杂的地方在于工作流状态：这次 run 进行到了哪一步、哪个步骤失败、产出了哪些结构化结果。

这些状态信息适合放在数据库里。

章节正文虽然也很重要，但它通常更长、会有多个版本，用对象存储管理更轻。Phase 1 最合适的方案是正文进 Storage，数据库只记录引用和索引。

#### P0 表

- `novels`：一本小说项目一条记录
- `chapters`：章节元数据，例如顺序、标题、状态、摘要
- `chapter_versions`：正文版本引用、来源 run 和 storage key
- `runs`：一次续写任务的状态机核心表
- `artifacts`：保存 outline、review、memory gate 等结构化结果

#### P1 表

- `character_cards`：人物卡和别名信息
- `memory_deltas`：候选记忆增量
- `merge_decisions`：人工处理合并或冲突的决策记录

#### 核心表说明

`runs` 至少应包含：

- `id`
- `novel_id`
- `base_chapter_id`
- `target_chapter_id`
- `state`
- `idempotency_key`
- `requirement_json`
- `current_outline_artifact_id`
- `current_review_artifact_id`
- `current_gate_artifact_id`
- `error_message`
- `created_at`
- `updated_at`

`chapter_versions` 至少应包含：

- `id`
- `chapter_id`
- `source_run_id`
- `version_number`
- `storage_bucket`
- `storage_key`
- `sha256`
- `created_at`

`artifacts` 至少应包含：

- `id`
- `run_id`
- `artifact_type`
- `version_number`
- `payload_json`
- `created_at`

#### 哪些内容放到 Storage

- `chapter.txt`
- 历史草稿
- 重写版本正文
- 较长调试日志

#### 实施顺序

1. 先确定 `PostgreSQL + Supabase`
2. 用 migration 建立 P0 五张表
3. 先跑通 `runs`、`artifacts` 和 `chapter_versions` 的保存链路
4. 再逐步补查询接口
5. 最后补人物卡和 merge 相关表

#### 完成标准

- 可以创建并追踪 run
- 可以从数据库查询结构化产物
- 可以从章节版本表拿到正文存储位置
- 不再依赖本地目录推断 run 状态

### 6.4 `apps/api`

这一层负责把 Engine 和持久化能力暴露成稳定后端接口。

#### 目标

- 提供最小可用 API
- 对外暴露 runs、chapters、artifacts 和 novel metadata
- 成为 Web 的单一数据入口

#### P0

- 初始化 FastAPI 项目结构
- 接入数据库和 repository 层
- 实现 `POST /runs`
- 实现 `GET /runs/{run_id}`
- 在创建 run 时持久化 requirement
- 在 run 完成后持久化 artifacts 和 chapter versions
- 统一错误响应结构

#### P1

- 实现 `GET /runs/{run_id}/artifacts`
- 增加章节列表和章节详情接口
- 支持 `idempotency_key` 防止重复提交
- 预留 worker 或异步任务集成
- 增加 gate 和 merge decision 相关接口

#### 完成标准

- Web 能通过 API 触发一次 run
- Web 能通过 API 查看 run 状态和结果
- API 返回稳定模型，而不是暴露本地文件路径假设

### 6.5 `apps/web`

这一层在 Phase 1 保持最小即可。

#### 目标

- 让用户能发起 run
- 让用户能看懂 run 结果
- 为后续人工确认和重写工作流预留位置

#### P0

- 初始化 Next.js App Router 项目
- 建立基础布局和导航
- 做小说列表页
- 做章节列表页
- 做 requirement 提交页
- 做 run 详情页
- 在 run 详情页展示 outline、chapter、review、memory gate

#### P1

- 增加轮询或实时刷新
- 增加 gate 审阅入口
- 增加人物卡入口
- 提升 requirement 表单体验
- 补空状态、加载状态和错误状态

#### 完成标准

- 用户无需翻服务器目录就能完成一次最小续写流程
- 用户能知道 run 当前在哪一步
- 用户能快速找到生成正文和 review 结果

### 6.6 `infra`、`docs` 与 `eval`

这一条线容易被忽略，但对长期维护非常关键。

#### 目标

- 让文档、环境配置和评测样本保持有序
- 降低后续接手和返工成本

#### P0

- 保留 `docs/phase1/` 作为 Phase 1 文档专区
- 为核心流程准备至少 10 个 evaluation case
- 约定日志、环境变量和本地启动方式
- 记录数据库迁移和初始化步骤
- 记录如何对照 Day6 基线验证结果

#### P1

- 增加 API 请求与响应示例
- 增加关键前端页面说明
- 增加 schema 草图或 ER 图
- 增加故障排查文档

#### 完成标准

- 新加入的人知道应该先看哪里
- 核心流程有样例和验证基线
- 文档不会再次碎成多个入口

## 7. 里程碑建议

### M0：冻结契约

- 完成 `packages/shared` 的 P0
- 明确 Phase 1 核心 schema 和枚举

### M1：封装引擎

- 完成 `packages/engine` 的 P0
- 让 Planner、Writer、Reviewer、Memory Curator 都能通过稳定入口调用

### M2：落地持久化

- 建好 P0 五张表
- 跑通 runs、artifacts、chapter versions 的保存

### M3：打通 API

- 完成 `POST /runs` 和 `GET /runs/{run_id}`
- 通过后端跑通一条完整续写链路

### M4：打通 Web

- 完成最小页面
- 用户可以提交 requirement 并查看 run 结果

### M5：收口验收

- 补齐基础 eval case
- 检查文档、错误处理和状态流
- 形成可持续迭代的 Phase 1 基线

## 8. 首批最优先任务

如果现在只问“下一步先做什么”，答案就是下面这 8 件：

1. 在 `packages/shared` 定义五个核心 schema：`continuation_req`、`outline`、`chapter_meta`、`review`、`memory_gate`
2. 在 `packages/shared` 定义 run 和 chapter 相关枚举
3. 盘点 Day6 输入输出并映射到 `packages/engine`
4. 设计并迁移数据库 P0 五张表
5. 打通正文进 Storage、结构化 artifacts 进数据库的保存流程
6. 在 `apps/api` 实现 `POST /runs`
7. 在 `apps/api` 实现 `GET /runs/{run_id}`
8. 在 `apps/web` 做 requirement 页面和 run 详情页

## 9. 风险与应对

### 风险 1：契约长期不稳定，导致各处返工

应对：优先做 `packages/shared`，让 API、数据库和 Web 都围绕它。

### 风险 2：Day6 逻辑直接泄漏到 API 层

应对：先做 engine 适配层，让 API 只调用 service。

### 风险 3：把所有文本都塞进数据库，后续难维护

应对：数据库只放元数据、状态和 JSON artifacts，长文本放 Storage。

### 风险 4：前端过早做复杂工作台，消耗太多精力

应对：Web 先聚焦最小提交和查看流程。

### 风险 5：文档再次越写越散，不知道先看哪份

应对：以后以这份主计划作为 Phase 1 唯一主入口。

## 10. 验收标准

当下面这些都满足时，可以认为 Phase 1 达标：

- 用户可以从 Web 提交一次续写 requirement
- 系统可以创建并追踪一条 run
- Planner、Writer、Reviewer、Memory Curator 的结果都能被保存和查看
- 章节正文和结构化产物都有清晰的存储位置
- 文档中定义的核心契约已经在代码中落地
- 团队不再需要手动翻目录判断 run 状态

## 11. 推荐阅读顺序

如果之后再回来看项目，建议按下面顺序阅读：

1. 先看这份主计划
2. 再看 `SPEC.md` 了解更完整的产品和契约背景
3. 真正实现时，再按需查看旧的 backlog 或数据库补充文档

从现在开始，这份文档就是 Phase 1 的主入口。