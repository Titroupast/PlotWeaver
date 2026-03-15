# PlotWeaver Phase 1 Plan

更新时间：2026-03-15

本文档基于 [SPEC.md](../../SPEC.md)、[PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md) 与 `novel-agent-day6/` 的当前事实实现，给出 PlotWeaver 的合理 Phase 1 落地计划。目标不是继续扩写愿景，而是把 Phase 1 收敛成一组可以直接拆任务、排期和验收的工作流。

---

## 1. 本次选用的本地 Skills

### 1.1 直接用于制定计划的 Skill

- `doc-coauthoring`
  - 用途：把计划文档写成真正给团队使用的交付文档，而不是松散的想法清单。
  - 本次作用：帮助明确受众、结构、章节顺序、实施重点和验收口径。

### 1.2 Phase 1 实施阶段建议搭配的本地 Skills

- `vercel-react-best-practices`
  - 用途：在 `apps/web/` 真正开始实现时，约束 Next.js / React 的数据流、边界划分和性能实践。
  - 触发时机：开始落 Web 控制台页面、数据获取和交互逻辑时。

- `web-design-guidelines`
  - 用途：在 Web 控制台初版出来后，检查可用性、可访问性、信息层级和交互质量。
  - 触发时机：Phase 1 UI 进入验收前。

本阶段不优先使用其他 skills 的原因：当前核心问题是 Phase 1 计划与交付顺序，不是部署、演示文稿或 Word 文档生产。

---

## 2. Phase 1 的一句话定义

Phase 1 的目标是：在不破坏 `novel-agent-day6/` 可运行性的前提下，把 PlotWeaver 升级为一个可部署、可审校、可追溯、可人工介入的 Web + API 写作工作台。

换句话说，Phase 1 不是做“完整版 PlotWeaver”，而是做出最小但完整的产品骨架：

- 用户可以从 Web 端发起续写 run。
- 系统能稳定产出提纲、正文、元数据、审校结果和记忆闸门结果。
- 关键结构化契约被冻结。
- 高风险记忆写回需要人工确认。
- run 能追踪、重试、查看结果。

---

## 3. Phase 1 范围边界

### 3.1 In Scope

Phase 1 必须完成：

1. 共享数据契约冻结
   - 冻结 `continuation_req.json`
   - 冻结 `outline.json`
   - 冻结 `chapter_meta.json`
   - 冻结 `review.json`
   - 冻结 `characters.json`
   - 冻结 `memory_gate.json` 最小结构

2. Engine 服务化最小闭环
   - 保持 `novel-agent-day6/` CLI 可运行
   - 把 Planner / Writer / Reviewer / Memory Curator 封装成 API 可调用能力
   - 形成 `run` 状态机主链路

3. Web 控制台 V1
   - 作品列表
   - 章节列表
   - 创建 run
   - 查看 outline / chapter / review / gate
   - 人工处理记忆闸门

4. 存储与追溯能力
   - DB 存元数据和结构化结果
   - Storage 存正文、草稿和长日志
   - run 记录输入 requirement、状态变更和产物版本引用

5. 最小回归与部署能力
   - 跑通最小 eval cases
   - 有基础健康检查和日志
   - 能把 Web/API 部署到可访问环境

### 3.2 Out of Scope

Phase 1 明确不做：

- 百万字级全文 RAG
- 动态多 Agent 编排平台
- 复杂计费与配额系统
- 原生移动端
- 多人实时协作编辑
- 自动化大规模评测平台

---

## 4. Phase 1 成功标准

Phase 1 完成后，PlotWeaver 至少要满足以下标准：

1. 从 Web 端可以创建一次续写 run，并拿到稳定结果。
2. 每个 run 至少能产出：`outline.json`、`chapter.txt`、`chapter_meta.json`、`review.json`。
3. `memory delta` 未过 gate 时，不会自动合并到主记忆。
4. 角色同名/化名/多身份冲突能进入人工确认，而不是自动污染 `characters.json`。
5. 同一个 run 的输入、状态、产物版本和错误信息都可追溯。
6. `novel-agent-day6/` CLI 仍然可用，作为事实基线不被破坏。

---

## 5. Phase 1 工作流拆解（Epics）

### Epic A. 冻结共享契约与目录语义

目标：把前后端、API、Engine 都会依赖的结构先固定下来，避免后续返工。

交付物：

- `SPEC.md` 中的结构化契约稳定
- `packages/shared/` 初始占位目录
- JSON Schema 或 Pydantic 模型
- 输入输出目录语义说明

关键任务：

- 定义 `continuation_req` schema
- 定义 `chapter_meta` schema
- 定义 `review` schema 的工程约束
- 定义 `character_id` 方案和 `merge_status` 规则
- 明确 `title.txt` 只是兼容文件

完成标准：

- API、Web、Engine 对相同契约不再各写一套解释
- 关键产物都能被 schema 校验

### Epic B. 抽离 Engine 并保住 Day6 CLI

目标：在不破坏 Day6 的前提下，把核心写作流程抽成可复用能力。

交付物：

- `packages/engine/` 设计方案或初始代码骨架
- Day6 CLI 对 engine 的复用入口
- 可被 API 直接调用的 Planner / Writer / Reviewer / Memory Curator

关键任务：

- 梳理 `app.py`、`tools.py`、prompt 依赖关系
- 把纯业务逻辑和 CLI 参数解析分开
- 统一输入输出对象
- 给每个步骤定义错误模型

完成标准：

- CLI 仍然能跑
- API 不需要复制一份 Day6 逻辑

### Epic C. 建设 API 与 Run 状态机

目标：把续写能力变成可调度、可追踪、可重试的服务。

交付物：

- `apps/api/` 初始 FastAPI 服务
- `POST /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/artifacts`
- run 状态机最小实现

关键任务：

- 创建 run 记录与 `idempotency_key`
- 定义状态推进顺序
- 为每个步骤保存产物版本引用
- 做最小错误处理与重试
- 预留队列化能力接口

完成标准：

- 后端可以从 requirement 开始，完整推进一次 run
- 失败时状态可见，结果可追踪

### Epic D. Web 控制台 V1

目标：把 CLI 的能力变成可操作的 Web 工作台。

交付物：

- `apps/web/` 初始 Next.js 项目
- 登录后的作品与章节页面
- 创建 run 页面或弹窗
- 产物查看页：outline / chapter / review / gate

关键任务：

- 设计作品和章节的信息层级
- 提供 requirement 编辑表单
- 展示 run 实时状态或轮询状态
- 提供最小错误反馈与重试入口

完成标准：

- 非开发者也能完成一次续写流程
- 用户无需进入文件目录就能查看主要产物

### Epic E. Memory Gate 与人工后台

目标：确保 Phase 1 的核心价值“可控写得对”真正落地。

交付物：

- `memory delta` 查看界面
- gate 结果面板
- 角色歧义待确认列表
- 人工通过 / 拒绝 / 编辑后合并入口

关键任务：

- 明确 gate 最小规则
- 明确 `PENDING_REVIEW` 和 `SPLIT_REQUIRED` 的处理流程
- 记录人工决策理由与操作人

完成标准：

- 高风险记忆变更不会自动入库
- 角色冲突问题在 Web 中可处理

### Epic F. 持久化、日志与最小评测

目标：让系统不仅能跑，还能复盘和迭代。

交付物：

- DB 表或最小模型设计
- Storage key 规范
- 结构化日志字段
- `eval_cases/` 与 `eval_runs/` 的最小工作流

关键任务：

- 定义 run、chapter、artifact 的存储引用结构
- 记录模型版本、输入 hash、错误信息
- 建立 10 到 20 个回归 case
- 支持简单的回归对比输出

完成标准：

- 每次改动都能拿固定 case 做最小回归
- 出问题时能追到具体 run 和具体阶段

---

## 6. 里程碑与推荐顺序

### M0. Phase 1 基线整理

目标：先收紧事实来源，避免边开发边改基础规则。

产出：

- 更新后的 `SPEC.md`
- 本文档 `docs/PHASE1_PLAN.md`
- 共享契约清单
- Day6 基线行为确认

### M1. Shared Contracts + Engine Skeleton

目标：先冻结合同，再开始服务化。

产出：

- 共享 schema
- engine 抽离方案
- 最小单元测试或校验脚本

### M2. API Run Pipeline

目标：先把主链路服务化，再去做 UI。

产出：

- `apps/api/` 可运行
- run 状态机主链路
- outline/chapter/review/gate 接口

### M3. Web Console Core Flow

目标：让用户能真正操作系统。

产出：

- 作品/章节列表页
- run 创建页
- run 结果查看页

### M4. Gate + Human Review

目标：把 PlotWeaver 和普通“AI 写文工具”真正区分开。

产出：

- 人工 gate 审批页
- 角色歧义处理页
- 操作留痕

### M5. Eval + Deploy

目标：让系统具备基本上线条件。

产出：

- 最小回归集
- 部署脚本或环境说明
- 健康检查、日志和最小监控

---

## 7. 关键路径

Phase 1 的关键路径应当是：

1. 冻结契约
2. 抽离 engine
3. 跑通 API run 主链路
4. 落 Web 核心页面
5. 补人工 gate
6. 补 eval 与部署

不建议的顺序：

- 先做大量前端页面，再回头补 API
- 先做全文级 RAG，再做 Phase 1 主链路
- 先做复杂计费，再做人工 gate
- 先把 Day6 重写掉，再做服务化

---

## 8. 建议的 Issue / Epic 结构

建议在项目管理工具里按下面方式拆：

1. `phase1-contracts`
   - requirement schema
   - chapter meta schema
   - review schema rules
   - characters merge rules

2. `phase1-engine`
   - extract planner service
   - extract writer service
   - extract reviewer service
   - extract memory curator service

3. `phase1-api`
   - create run endpoint
   - get run status endpoint
   - persist artifacts
   - implement state machine

4. `phase1-web`
   - project/chapter list
   - requirement editor
   - run detail panel
   - artifact viewer

5. `phase1-gate`
   - gate rules
   - manual review API
   - merge decision UI

6. `phase1-eval-deploy`
   - eval cases seed
   - regression runner
   - deployment docs
   - health checks

---

## 9. 风险与缓解策略

### 风险 1：计划写得很合理，但实际工作量失控

缓解：

- 所有任务都围绕 Phase 1 成功标准，不把 Phase 2 内容偷渡进来。
- 每个 epic 都要求有清晰“完成标准”，而不是只有方向。

### 风险 2：Web 和 API 同时开工，合同不一致

缓解：

- 所有接口先以共享 schema 为准。
- Web 不直接猜字段，API 不直接猜页面需求。

### 风险 3：角色记忆仍然发生错误合并

缓解：

- 在 Phase 1 就落 `character_id` 与人工确认入口。
- 把“自动合并”从默认路径中拿掉。

### 风险 4：CLI 被服务化改坏

缓解：

- 把 Day6 作为回归基线。
- 每轮抽离后都验证 CLI 主流程还能跑通。

### 风险 5：做了 UI，但没有真实评测能力

缓解：

- 在 Phase 1 就建立最小 eval case 集。
- 每次主链路变更都跑回归，而不是等临上线再测。

---

## 10. Phase 1 Exit Criteria

只有同时满足以下条件，Phase 1 才算完成：

- `novel-agent-day6/` CLI 可继续运行。
- Web 端可创建并查看 run。
- API 能稳定产出并保存 outline / chapter / chapter_meta / review / gate。
- 角色冲突和高风险 memory delta 进入人工处理流程。
- 有一套可重复执行的最小回归样例。
- 有清晰的部署方式和基础运行观测能力。

---

## 11. 下一步建议

如果继续往下推进，建议严格按下面顺序执行：

1. 把共享 schema 和 engine 抽离方案落实到目录和代码骨架。
2. 先做 API 主链路，不先铺太多页面。
3. Web 只做 Phase 1 核心流程所需页面。
4. 提前把人工 gate 和角色歧义入口做出来。
5. 最后再补 eval、部署和体验打磨。

这份计划的作用，是把 Phase 1 从“想做一个全栈 AI 写作平台”收紧成“先做出一个稳定、可控、可交付的写作工作台”。
