## PlotWeaver Web (Next.js App Router)

### Quick start

```powershell
cd apps/web
npm install
npm run dev
```

### Environment variables

Create `apps/web/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_TENANT_ID=00000000-0000-0000-0000-000000000001
```

### Implemented Task E pages

- `/app/projects`
- `/app/projects/[projectId]`
- `/app/projects/[projectId]/chapters/[chapterId]/configure`
- `/app/projects/[projectId]/chapters/[chapterId]/runs/[runId]`
- `/app/projects/[projectId]/chapters/[chapterId]/runs/[runId]/review`
