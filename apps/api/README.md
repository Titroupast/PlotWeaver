API app (FastAPI) placeholder.

## Task C: DB setup

### Install

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
uv pip install -e .
```

### Run migrations

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/plotweaver"
alembic upgrade head
```

### Optional backfill from Day6 files

```powershell
Set-Location D:\github_projects\PlotWeaver\apps\api
python scripts/backfill_day6_to_db.py
```

### RLS tenant context in app code

Each request/transaction should set:

```sql
SET LOCAL app.current_tenant_id = '<tenant_uuid>';
```
