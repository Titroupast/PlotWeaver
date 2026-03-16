# PlotWeaver 部署视图

## 环境分层
| 环境 | 目的 | Web | API | 数据库 |
| --- | --- | --- | --- | --- |
| dev | 本地开发与调试 | `npm run dev` | 本地 uvicorn / docker | 本地 postgres |
| staging | 发版前验证 | Vercel 预发布域名 | 容器平台 staging 服务 | Supabase staging 项目 |
| prod | 线上流量 | Vercel 生产域名 | 容器平台 production 服务 | Supabase production 项目 |

## 发布流
1. 代码合并到 `main`。
2. CI 门禁通过（contract + api + web e2e）。
3. Web 发布到 Vercel。
4. API 镜像发布到容器平台（先 staging 后 prod）。
5. 发布阶段执行 Alembic 迁移。

## 回滚策略
1. Web：在 Vercel 回滚到上一个稳定 deployment。
2. API：回滚到上一个镜像 tag。
3. DB：优先前向修复；严重故障时恢复快照。

## Phase 1 运行指标（基线）
- API 可用性：99.5%
- `runs` 相关读接口 P95 延迟：< 800ms
- SSE 事件延迟 P95：< 3s
- 月度发布失败率：< 5%
