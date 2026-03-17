API 应用（FastAPI）说明。

## Task B + C 快速开始

### 安装

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
uv pip install -e .
```

如果你是直接用 `.venv\Scripts\python.exe` 启动 API，请确保同一解释器已安装依赖：

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
D:\github_projects\PlotWeaver\.venv\Scripts\python.exe -m pip install -e .
```

### 启动 API

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
$env:ARK_API_KEY="<你的ARK密钥>"
$env:ARK_MODEL="<你的模型ID>"
uvicorn plotweaver_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
```

说明：
- 若配置了 `ARK_API_KEY` + `ARK_MODEL`，编排步骤会调用真实大模型生成每步结果。
- 若未配置，上述步骤会回退为本地生成逻辑（用于本地联调）。
- 环境变量读取优先级：`apps/api/.env` -> 仓库根目录 `.env` -> `novel-agent-day6/.env`（兼容旧配置）。

### LLM 配置自检

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
D:\github_projects\PlotWeaver\.venv\Scripts\python.exe scripts/check_llm_setup.py
```

输出应满足：
- `openai_installed: True`
- `ark_api_key_set: True`
- `ark_model` 非空

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
- `/api/v1/projects/{project_id}/chapters/{chapter_id}/latest-content`
- `/api/v1/projects/{project_id}/requirements`
- `/api/v1/runs/*`
- `/api/v1/runs/{run_id}/artifacts`
- `/api/v1/memory/projects/{project_id}/*`

### 分步执行（PLANNER -> WRITER -> REVIEWER -> MEMORY_CURATOR）

- `POST /api/v1/runs/{run_id}/execute` 默认执行单步并进入 `WAITING_USER_APPROVAL`。
- 前端在每步后展示当前产物，用户点击“继续下一步”再推进。
- 若需一次跑完整条链路：`POST /api/v1/runs/{run_id}/execute` body 传 `{ "auto_continue": true }`。

### 提示词模板位置

- `apps/api/src/plotweaver_api/prompts/planner_system.txt`
- `apps/api/src/plotweaver_api/prompts/planner_user.txt`
- `apps/api/src/plotweaver_api/prompts/writer_system.txt`
- `apps/api/src/plotweaver_api/prompts/writer_user.txt`
- `apps/api/src/plotweaver_api/prompts/reviewer_system.txt`
- `apps/api/src/plotweaver_api/prompts/reviewer_user.txt`
- `apps/api/src/plotweaver_api/prompts/memory_curator_system.txt`
- `apps/api/src/plotweaver_api/prompts/memory_curator_user.txt`

### 正文存储说明（Phase 1）

- Writer 生成正文后，文本写入本地 Storage（默认目录 `apps/api/.local_storage`，可通过 `storage_local_root` 调整）。
- `chapter_versions` 保存正文版本元信息（`storage_bucket/storage_key/content_sha256/byte_size/source_run_id` 语义）。
