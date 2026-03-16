## 基础设施总览

Phase 1 的部署目标如下：

1. Web（`apps/web`）：Vercel。
2. API（`apps/api`）：独立容器服务。
3. 数据库：Supabase PostgreSQL。
4. 对象存储：Supabase Storage（或 S3 兼容存储）。

参考文档：

- `docs/phase1/DEPLOYMENT_PHASE1_BLUEPRINT.md`
- `docs/runbook/README.md`
- `architecture/viewpoints/context.md`
- `architecture/viewpoints/containers.md`
- `architecture/viewpoints/deployment.md`
