# PlotWeaver 部署蓝图（Phase 1）

日期：2026-03-17  
状态：进行中

## 1. 目标拓扑
1. Web：`apps/web` 部署在 Vercel。
2. API：`apps/api` 部署在独立容器服务。
3. 数据：Supabase PostgreSQL（可选 Supabase Storage / S3 兼容对象存储）。

## 2. 环境分层
| 环境 | 用途 | 发布策略 |
| --- | --- | --- |
| dev | 本地开发与调试 | 手动 |
| staging | 发布前验证 | 从 main/staging 分支自动部署 |
| prod | 正式流量 | 审批后发布 |

## 3. 环境变量策略
### Web（Vercel）
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_TENANT_ID`

### API（容器服务）
- `APP_ENV`
- `APP_DEBUG`
- `API_PREFIX`
- `DATABASE_URL`
- `DEFAULT_TENANT_ID`
- `SENTRY_DSN`（建议）

规则：
1. 密钥不入库。
2. 各环境使用独立密钥。
3. 每 90 天轮换，或在安全事件后立即轮换。

## 4. 发布流程
1. 合并代码到目标分支。
2. CI 门禁通过（contract/api/e2e）。
3. 部署 Web（Vercel Preview 或 Production）。
4. 部署 API 镜像到 staging/prod。
5. API 发布窗口执行迁移（`alembic upgrade head`）。

## 5. 回滚流程
1. Web：在 Vercel 回滚到上一版本。
2. API：部署上一镜像 Tag。
3. DB：优先前向修复；仅严重场景使用快照恢复。

## 6. 监控与告警
1. 运行时错误：Sentry。
2. 健康与可用性：Uptime 检查。
3. 成本：Vercel + 容器平台 + Supabase 月预算阈值。
4. 值班等级：
   - P1：服务中断或核心接口不可用
   - P2：服务降级
   - P3：一般告警

## 7. 责任归属
1. Web 发布负责人：前端维护者。
2. API 发布负责人：后端维护者。
3. DB 迁移负责人：后端/数据库维护者。
4. 事件总协调：当周值班工程师。

## 8. Task H 交付物
1. API 容器构建定义（`apps/api/Dockerfile`）。
2. 架构视图文档（`architecture/viewpoints/*`）。
3. 运行手册目录（`docs/runbook/*`）。
4. CI 部署工作流蓝图（`.github/workflows/deploy-*.yml`）。
