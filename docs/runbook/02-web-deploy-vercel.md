# 02 Web 部署（Vercel）

## 范围
将 `apps/web` 部署到 Vercel，支持 Preview 与 Production。

## 分支策略
1. 功能分支推送：触发 Vercel Preview。
2. `main` 合并：触发 Vercel Production。

## 配置步骤
1. 在 Vercel 创建项目并指向 `apps/web`。
2. Root Directory 设为 `apps/web`。
3. 按环境配置变量：
   - `NEXT_PUBLIC_API_BASE_URL`
   - `NEXT_PUBLIC_TENANT_ID`

## 回滚步骤
1. 打开 Vercel Deployments。
2. 选择最近稳定版本。
3. Promote 到 Production。
4. 验证 `/app/projects` 与 run 详情页。

## 发布后检查
1. 首页重定向正常（`/` -> `/app/projects`）。
2. 续写配置表单可提交。
3. 生成过程页能显示流状态。
4. 结果审阅页可渲染 artifacts。
