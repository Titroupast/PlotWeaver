API 应用（FastAPI）说明。

## Task B + C 快速开始

### 安装

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
uv pip install -e .
```

### 启动 API

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
uvicorn plotweaver_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
```

### 使用 Docker 运行

在仓库根目录构建并启动：

```powershell
Set-Location D:\github_projects\PlotWeaver
docker build -f apps/api/Dockerfile -t plotweaver-api:local .
docker run --rm -p 8000:8000 --env-file apps/api/.env.example plotweaver-api:local
```

### 执行数据库迁移

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
D:\github_projects\PlotWeaver\.venv\Scripts\alembic.exe upgrade head
```

### 可选：从 Day6 文件回填数据库

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
python scripts/backfill_day6_to_db.py
```

### 应用内 RLS 租户上下文

每个请求/事务应设置：

```sql
SELECT set_config('app.current_tenant_id', '<tenant_uuid>', true);
```

当前实现读取 `x-tenant-id` 请求头，本地开发默认值为
`00000000-0000-0000-0000-000000000001`。

### 运行测试（Phase 2）

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
python -m pytest -q
```

### Phase 2 关键 API 分组

- `/api/v1/health/*`
- `/api/v1/projects/*`
- `/api/v1/projects/{project_id}/chapters`
- `/api/v1/projects/{project_id}/requirements`
- `/api/v1/runs/*`
- `/api/v1/runs/{run_id}/artifacts`
- `/api/v1/memory/projects/{project_id}/*`
