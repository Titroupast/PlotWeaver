API app (FastAPI) placeholder.

## Task B + C quickstart

### Install

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
uv pip install -e .
```

### Run API

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
uvicorn plotweaver_api.main:app --host 0.0.0.0 --port 8000 --app-dir src
```

### Run migrations

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
D:\github_projects\PlotWeaver\.venv\Scripts\alembic.exe upgrade head
```

### Optional backfill from Day6 files

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/plotweaver"
python scripts/backfill_day6_to_db.py
```

### RLS tenant context in app code

Each request/transaction should set:

```sql
SET LOCAL app.current_tenant_id = '<tenant_uuid>';
```

Current implementation uses `x-tenant-id` header and defaults to
`00000000-0000-0000-0000-000000000001` for local development.
### Run tests (Phase 2)

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
python -m pytest -q
```

### Key API groups in Phase 2

- `/api/v1/health/*`
- `/api/v1/projects/*`
- `/api/v1/projects/{project_id}/chapters`
- `/api/v1/projects/{project_id}/requirements`
- `/api/v1/runs/*`
- `/api/v1/runs/{run_id}/artifacts`
- `/api/v1/memory/projects/{project_id}/*`
