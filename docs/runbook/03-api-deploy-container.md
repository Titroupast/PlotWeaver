# 03 API 部署（容器）

## 适用范围
将 `apps/api` 以独立容器服务方式部署。

## 构建命令
在仓库根目录执行：

```bash
docker build -f apps/api/Dockerfile -t plotweaver-api:<tag> .
```

## 运行命令
```bash
docker run -p 8000:8000 --env-file apps/api/.env.example plotweaver-api:<tag>
```

## 必需密钥
- `DATABASE_URL`
- `DEFAULT_TENANT_ID`
- `APP_ENV`
- `APP_DEBUG`
- `API_PREFIX`
- `SENTRY_DSN`（建议配置）

## 迁移步骤
切流量前执行：

```bash
alembic upgrade head
```

## 回滚步骤
1. 重新部署上一个镜像 Tag。
2. 验证 `/api/v1/health/live`。
3. 验证 `/api/v1/runs` 读取链路。

## 发布后冒烟检查
1. 健康检查接口返回 200。
2. `GET /api/v1/projects` 可正常响应。
3. `GET /api/v1/runs?project_id=<id>` 可正常响应。
