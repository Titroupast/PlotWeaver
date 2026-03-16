# 05 密钥管理与轮换

## 密钥分类
1. 公共配置（`NEXT_PUBLIC_*`）：仅允许非敏感信息。
2. 应用密钥（`DATABASE_URL`、Token、DSN 等）。
3. CI 密钥（镜像仓库凭据、部署凭据）。

## 存储规范
1. Web 端密钥使用 Vercel 环境变量管理。
2. API 密钥使用容器平台 Secret Manager。
3. CI 专用凭据使用 GitHub Actions Secrets。
4. 禁止将任何密钥提交到仓库。

## CI 最小密钥清单
1. `VERCEL_TOKEN`
2. `VERCEL_ORG_ID`
3. `VERCEL_PROJECT_ID`
4. 容器仓库凭据（若不使用 `GITHUB_TOKEN`）
5. 部署平台 Token（Render/Fly/Railway/K8s 自动化）

## 轮换策略
1. 常规轮换周期：90 天。
2. 人员离职或疑似泄漏时立即轮换。
3. 轮换记录写入发布变更日志。

## 事件处置规则
若怀疑密钥泄漏：
1. 立即吊销当前密钥。
2. 轮换所有下游依赖密钥。
3. 审计近期访问日志。
