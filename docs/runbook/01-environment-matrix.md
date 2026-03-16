# 01 环境矩阵

## 环境隔离
| 项目 | dev | staging | prod |
| --- | --- | --- | --- |
| Web 地址 | localhost:3000 | 预发布域名 | 生产域名 |
| API 地址 | localhost:8000 | staging API 域名 | production API 域名 |
| DB | 本地 docker postgres | Supabase staging | Supabase production |
| 数据保留 | 可清理 | 中等保留 | 严格保留 |
| 访问控制 | 团队开发 | 限定人员 | 最小权限 |

## 必要变量
### Web
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_TENANT_ID`

### API
- `APP_ENV`
- `APP_DEBUG`
- `API_PREFIX`
- `DATABASE_URL`
- `DEFAULT_TENANT_ID`
- `SENTRY_DSN`（建议）

## 规则
1. 生产密钥禁止在非生产环境使用。
2. 仅 `main` 分支允许生产发布。
3. 环境变量变更必须写入发布记录。
