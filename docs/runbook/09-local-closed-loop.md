# 本地闭环运行手册（Phase 1）

## 1. 目标
本手册用于本地完成最小闭环：
1. 创建项目
2. 创建 requirement 并启动 run
3. 观察 run 事件流
4. 查看结构化 artifacts 与最新正文

## 2. 启动顺序

### 2.1 启动 PostgreSQL（Docker）
在仓库根目录执行：

```powershell
docker compose up -d postgres
```

### 2.2 迁移数据库

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
D:\github_projects\PlotWeaver\.venv\Scripts\alembic.exe upgrade head
```

### 2.3 可选：回填 Day6 数据

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
D:\github_projects\PlotWeaver\.venv\Scripts\python.exe scripts/backfill_day6_to_db.py
```

### 2.4 启动 API

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
D:\github_projects\PlotWeaver\.venv\Scripts\python.exe -m uvicorn plotweaver_api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2.5 启动 Web

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\web
npm install
npm run dev
```

打开 `http://localhost:3000/app/projects`。

## 3. 最小验收清单
1. 在 Projects 页创建项目成功。
2. 进入项目后可看到章节并进入 Configure 页面。
3. 提交 requirement 后自动创建 run 并进入运行页。
4. 运行页可看到事件流与 Run 状态。
5. Review 页面可展示 `OUTLINE/CHAPTER_META/REVIEW/MEMORY_GATE`。
6. 运行页可查看最新正文（Latest Chapter Content）。

## 4. 数据落点说明
1. 结构化产物：`run_artifacts`。
2. 正文文本：本地 storage（默认 `./.local_storage`）。
3. 章节版本追踪：`chapter_versions`（含 `storage_bucket/storage_key/content_sha256/byte_size`）。

## 5. 常见联调错误

### 5.1 tenant 不匹配
现象：接口 404/空数据，但数据库有数据。
排查：确认请求头 `x-tenant-id` 与目标数据 tenant 一致。

### 5.2 CORS 预检失败
现象：浏览器报 `No 'Access-Control-Allow-Origin'`。
排查：确认 API 启动在 `127.0.0.1:8000`，前端在 `localhost:3000` 或 `127.0.0.1:3000`，并未被代理改写。

### 5.3 run_id / project_id 混用
现象：查询 artifacts 或 events 报错 uuid 无效。
排查：`/runs/{run_id}/...` 必须传 run id，不可传 tenant id 或 project id。

### 5.4 SSE 中断
现象：run 页面流状态从 `STREAMING` 变为 `STALE`。
机制：前端自动指数退避重连；重试多次后降级到轮询（`POLLING`）。
排查：优先确认 API 是否仍可访问 `GET /api/v1/runs/{run_id}`。