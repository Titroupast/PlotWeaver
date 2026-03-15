# PlotWeaver 环境配置指南（Phase 1）

本指南用于 Day6 Python 管线向 FastAPI + Next.js 迁移阶段。  
目标：先把后端开发环境标准化，保证 契约优先落地。

## 1. 前置要求

- OS: Windows 10/11（本文命令以 PowerShell 为例）
- Python: 3.11 或 3.12
- Node.js: 20 LTS（前端 Next.js 使用）
- Git: 最新稳定版

建议统一使用 uv 管理 Python 虚拟环境和依赖。

## 2. 后端 Python 环境初始化

在仓库根目录执行：

`powershell
Set-Location D:\github_projects\PlotWeaver
python -m pip install -U pip uv
uv venv
.\.venv\Scripts\Activate.ps1
`

验证：

`powershell
python --version
uv --version
`

## 3. 依赖安装（按模块）

### 3.1 后端核心

`powershell
uv pip install fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy>=2.0 alembic httpx
`

数据库驱动二选一：

`powershell
# 推荐：通用稳定
uv pip install psycopg[binary]

# 可选：纯 async 路线
# uv pip install asyncpg
`

### 3.2 认证与安全

二选一 JWT 库：

`powershell
# 方案 A（推荐）
uv pip install python-jose[cryptography] passlib[bcrypt]

# 方案 B
# uv pip install pyjwt passlib[bcrypt]
`

### 3.3 异步任务与流式（可选）

`powershell
# RQ 路线
uv pip install redis rq sse-starlette

# Celery 路线（二选一，不与 RQ 混用）
# uv pip install redis celery sse-starlette
`

### 3.4 契约与质量

`powershell
uv pip install jsonschema orjson
`

### 3.5 测试与可观测性

`powershell
uv pip install pytest pytest-asyncio respx opentelemetry-sdk opentelemetry-instrumentation-fastapi structlog
`

## 4. .env 配置模板（后端）

在后端服务目录放置 .env（例如未来 pps/api/.env）：

`env
# App
APP_NAME=PlotWeaver API
APP_ENV=dev
APP_DEBUG=true
APP_PORT=8000
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/plotweaver

# Auth
JWT_ISSUER=https://your-auth-issuer.example.com
JWT_AUDIENCE=plotweaver-api
JWT_JWKS_URL=https://your-auth-issuer.example.com/.well-known/jwks.json
JWT_ALGORITHM=RS256

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Storage (optional)
STORAGE_BUCKET=plotweaver-dev
STORAGE_ENDPOINT=
STORAGE_REGION=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=

# Observability (optional)
OTEL_SERVICE_NAME=plotweaver-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
`

## 5. 前端环境（Next.js）简版

如果后续新建前端应用（例如 pps/web）：

`powershell
Set-Location D:\github_projects\PlotWeaver\apps\web
npm install
`

前端 .env.local 常用项：

`env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
`

## 6. 启动约定（Phase 1）

- 后端 API：http://localhost:8000
- OpenAPI：http://localhost:8000/docs
- 前端 Web：http://localhost:3000

建议先只打通：

1. 健康检查接口
2. 契约校验接口（outline/review/characters）
3. 生成任务提交 + 状态查询（可先轮询，后续再 SSE）

## 7. 常见问题

### PowerShell 执行策略导致脚本报错

若出现 禁止运行脚本，可临时使用无配置模式执行：

`powershell
powershell -NoProfile -Command uv --version
`

### psycopg 安装异常

优先使用：

`powershell
uv pip install psycopg[binary]
`

如果团队统一 async 驱动，再切换到 syncpg。

### RQ 与 Celery 怎么选

- 小团队、快速落地：RQ
- 复杂任务编排、多队列和更高扩展性：Celery

同一阶段建议只选一个，避免运维复杂度上升。

## 8. 推荐的下一步

1. 固化 pyproject.toml 依赖分组（core/dev/obs/worker）
2. 新增 pps/api 并放置最小 FastAPI 骨架
3. 先实现契约模型（Pydantic）再接入业务路由
