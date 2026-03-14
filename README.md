# PlotWeaver

PlotWeaver 是一个面向中文轻小说“续写/连载”的生成式写作系统：规划（outline）→ 写作（chapter）→ 审校（review）→ 记忆增量（memory delta）→ 人工闸门（human gate）→ 合并主记忆。


## 核心流程

- 规划 → 写作 → 审校 → 记忆增量 → 人工闸门（通过/拒绝/编辑后合并）
- 三层记忆：事实层（结构化、可引用）/摘要层（压缩总结）/提示层（run 内临时组装，不作为权威记忆）

## 当前起点（Day6）

- 当前仓库内的参考实现以 `novel-agent-day6/` 为事实来源。
- 本仓库已删除 Day1–Day5 的历史原型产物；如需回看可通过 Git 历史找回。

## 快速开始（运行 Day6 CLI）

1. 安装依赖

- `pip install -r novel-agent-day6/requirements.txt`

2. 配置环境变量（在 `novel-agent-day6/.env` 或系统环境变量中）

- `ARK_API_KEY=...`
- `ARK_MODEL=...`
- `ARK_BASE_URL=...`（可选，默认已内置）

3. 准备输入

- 参考 `novel-agent-day6/USAGE.md` 的 `inputs/<novel_id>/chapters/` 与 `inputs/<novel_id>/memory/` 结构。

4. 生成下一章（示例）

- `python novel-agent-day6/app.py --novel-id demo --chapter-id chapter_004`

## 文档

- 规格文档：`SPEC.md`
- 项目结构：`PROJECT_STRUCTURE.md`
- Agent 工作约定：`AGENTS.md`

## 目标（全栈）

- Web：Next.js
- API：FastAPI（把 Day6 管线服务化）
- DB：PostgreSQL
- Storage：对象存储保存章节/草稿等长文本
- Mobile（后续）：Expo（React Native）
