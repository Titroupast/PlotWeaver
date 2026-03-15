# PlotWeaver Phase 1 Backlog

更新时间：2026-03-15

这份 backlog 只做一件事：把 Phase 1 变成“下一步直接能开工的任务清单”。

优先级说明：

- `P0`：不做就跑不通 Phase 1 主链路
- `P1`：主链路跑通后必须补齐的任务
- `P2`：Phase 1 内可做但不阻塞首版上线的任务

---

## 1. 先后顺序

当前最合理的推进顺序是：

1. `packages/shared`
2. `packages/engine`
3. 数据库 / Storage
4. `apps/api`
5. `apps/web`
6. gate / merge decision
7. eval / infra / docs

不要反过来做：先做大量 UI，再回头补 API 和契约。

---

## 2. `packages/shared`

### P0

- 建立 `schemas/`、`constants/`、`examples/`
- 定义 `continuation_req` schema
- 定义 `outline` schema
- 定义 `chapter_meta` schema
- 定义 `review` schema
- 定义 `memory_gate` schema
- 定义 `character_card` 最小结构
- 定义 run state、chapter status、chapter kind 枚举

### P1

- 补齐 API 公共响应模型
- 为每个 schema 增加示例文件
- 增加 schema 校验脚本

---

## 3. `packages/engine`

### P0

- 盘点 `novel-agent-day6/` 里 CLI 和引擎的边界
- 携建 `planner/`、`writer/`、`reviewer/`、`memory/` 目录
- 抽离 Planner 入口
- 抽离 Writer 入口
- 抽离 Reviewer 入口
- 抽离 Memory Curator 入口
- 把文件 IO 和纯业务逻辑分开
- 确保 Day6 CLI 继续可运行

### P1

- 统一 DTO
- 统一错误模型
- 统一 prompt 加载方式
- 增加最小回归脚本

---

## 4. 数据库 / Storage

### P0

- 确定 PostgreSQL + Supabase
- 确定 Supabase Storage 或 S3 兼容方案
- 建最小表结构：
  - `novels`
  - `chapters`
  - `chapter_versions`
  - `runs`
  - `artifacts`
- 确定正文进 Storage，元数据进 DB
- 建 migration 目录
- 写本地连接说明

### P1

- 补 `character_cards`
- 补 `memory_deltas`
- 补 `merge_decisions`
- 增加基础索引
- 定义 Storage key 规范
- 定义 repository 分层

### 数据库这条线的核心理解

- `runs` 是最重要的表
- `chapters` 管理章节元数据
- `chapter_versions` 记录正文版本和 Storage 引用
- `artifacts` 存 outline / review / gate 这些 JSON 结果

---

## 5. `apps/api`

### P0

- 初始化 FastAPI 项目
- 健康检查接口
- `POST /runs`
- `GET /runs/{run_id}`
- run 状态推进主链路
- artifact 保存逻辑
- chapter version 保存逻辑
- 最小错误响应模型

### P1

- `GET /runs/{run_id}/artifacts`
- gate 审批接口
- merge decision 接口
- `idempotency_key` 去重
- 结构化日志
- worker / 后台任务封装

---

## 6. `apps/web`

### P0

- 初始化 Next.js App Router
- 基础布局和导航
- 小说列表页
- 章节列表页
- requirement 表单
- run 详情页
- 展示 outline / chapter / review / gate
- 基础错误态和空态

### P1

- run 轮询或刷新逻辑
- gate 审批页
- 角色歧义处理页
- run 状态过滤与搜索
- requirement 表单校验提示

---

## 7. `infra` / `docs` / `eval`

### P0

- 列出环境变量
- 约定本地启动方式
- 写最小部署说明
- 维护 `docs/phase1/` 导航
- 确定首批 10 个 eval case

### P1

- `DB_SCHEMA_DRAFT.md`
- API 设计草案
- Web 页面说明
- 评测结果模板

---

## 8. 本周先做的 5 件事

如果现在只能开工一小段，就先做这 5 件：

1. 定义 `continuation_req` / `outline` / `chapter_meta` / `review` schema
2. 盘点 Day6 边界，准备抽离 engine
3. 设计最小 DB 表结构（`novels` / `chapters` / `chapter_versions` / `runs` / `artifacts`）
4. 初始化 `apps/api`，先实现 `POST /runs` 和 `GET /runs/{run_id}`
5. 初始化 `apps/web`，先做列表页 + run 详情页骨架

---

## 9. 阻塞关系

- `packages/shared` 没稳定前，不要大量写 `apps/web` 表单
- `packages/engine` 没抽离前，`apps/api` 很容易复制 Day6 逻辑
- DB 结构没稳定前，`apps/api` repository 层会频繁返工
- gate 和 merge decision 没明确前，角色记忆不要默认自动化

---

## 10. 维护建议

- 每条任务都标 `P0 / P1 / P2`
- 每条任务都写清依赖
- 完成后更新状态，不重写整份文档
- Phase 1 相关文档统一放在 `docs/phase1/`

这份 backlog 的目的，是让你现在就知道“先做哪些事”。
