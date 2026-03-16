## PlotWeaver Web（Next.js App Router）

### 快速开始

```powershell
cd apps/web
npm install
npm run dev
```

### 环境变量

创建 `apps/web/.env.local`：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_TENANT_ID=00000000-0000-0000-0000-000000000001
```

如果部署到 Vercel，请在项目环境变量中同步配置以上变量（Preview / Production）。

### 已实现的 Task E 页面

- `/app/projects`
- `/app/projects/[projectId]`
- `/app/projects/[projectId]/chapters/[chapterId]/configure`
- `/app/projects/[projectId]/chapters/[chapterId]/runs/[runId]`
- `/app/projects/[projectId]/chapters/[chapterId]/runs/[runId]/review`
