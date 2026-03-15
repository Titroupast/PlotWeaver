# PlotWeaver DB Phase 1 Plan

更新时间：2026-03-15

这份文档专门回答一个问题：PlotWeaver 的数据库在 Phase 1 应该怎么实现，才能既容易上手，又能支撑后续服务化。

如果你没有学过数据库，也没关系。你现在只需要先建立一个正确认知：

- 数据库不是拿来保存所有文本内容的。
- 数据库主要负责“结构化信息、状态、关系和检索”。
- 章节正文、草稿、长日志这类大文本，应该放到 Storage。

所以对 PlotWeaver 来说，最实用的 Phase 1 方案是：

- 数据库：PostgreSQL
- 托管方案：Supabase
- 对象存储：Supabase Storage 或 S3 兼容方案
- 应用层：FastAPI + SQLModel/SQLAlchemy

---

## 1. 先用一句话理解数据库在这个项目里的职责

数据库负责回答这些问题：

- 这本小说有哪些章节？
- 这一章的标题、摘要和状态是什么？
- 这次 run 跑到哪一步了？
- 这次 review 分数是多少？
- 这个角色是不是待人工确认？

数据库不负责回答这些问题：

- 第五章正文全文是什么？
- 某次草稿的完整长文本是什么？
- 某次超长日志全文是什么？

这些“大文本内容”应该进 Storage。

你可以这样理解：

- 数据库：图书馆目录系统
- Storage：真正放书内容的书库

---

## 2. 为什么 Phase 1 选 PostgreSQL / Supabase

### PostgreSQL 的好处

- 稳定
- 文档多
- 适合结构化数据
- 支持 JSONB，适合存 `outline/review/gate` 这类结构化结果
- 后续能扩展全文检索和向量能力

### Supabase 的好处

- 自带 Postgres
- 自带 Auth
- 自带 Storage
- 对新手更友好
- 后续做 Web 登录、对象存储、RLS 都方便

Phase 1 最重要的是降低系统搭建成本，所以 Supabase 很适合。

---

## 3. 什么放数据库，什么放 Storage

### 放数据库的内容

- 用户与作品元数据
- 章节元数据
- run 状态机
- outline/review/gate 等结构化 JSON
- 角色卡和记忆 delta 元数据
- 人工 merge decision 记录

### 放 Storage 的内容

- `chapter.txt` 正文
- 草稿版本全文
- 长日志
- 将来可能的大块上下文快照

### 一个简单判断方法

如果一段内容：

- 很长
- 经常整段读写
- 不适合按字段筛选

那它更适合放 Storage。

如果一段内容：

- 需要按字段查询
- 需要关联别的对象
- 需要作为状态或索引存在

那它更适合放数据库。

---

## 4. Phase 1 最小表结构

Phase 1 建议先做 8 张核心表，已经足够支撑主链路。

### 4.1 `novels`

作用：一部作品一条记录。

建议字段：

- `id`
- `owner_user_id`
- `title`
- `description`
- `language`
- `status`
- `created_at`
- `updated_at`

### 4.2 `chapters`

作用：记录章节元数据，对应 `chapter_meta.json` 的核心信息。

建议字段：

- `id`
- `novel_id`
- `chapter_key` 例如 `chapter_005`
- `kind`
- `title`
- `subtitle`
- `volume_id` 可空
- `arc_id` 可空
- `order_index`
- `status`
- `summary`
- `created_at`
- `updated_at`

说明：

- 这里不直接存正文全文。
- 标题永远来自这里，而不是正文第一行。

### 4.3 `chapter_versions`

作用：一章可以有多个正文版本，比如第一次生成、重写版、人工修订版。

建议字段：

- `id`
- `chapter_id`
- `version_no`
- `source_type` 例如 `GENERATED` / `MANUAL` / `REWRITE`
- `storage_bucket`
- `storage_key`
- `content_sha256`
- `byte_size`
- `created_by`
- `created_at`

说明：

- 正文全文在 Storage。
- 数据库只记录“这份正文文件放在哪”。

### 4.4 `runs`

作用：这是 Phase 1 最重要的表，记录一次续写任务的全过程。

建议字段：

- `id`
- `novel_id`
- `base_chapter_id`
- `target_chapter_id`
- `state`
- `idempotency_key`
- `requirement_json`
- `requirement_hash`
- `error_code`
- `error_message`
- `attempt_count`
- `created_by`
- `created_at`
- `updated_at`

说明：

- `state` 对应 run 状态机。
- `requirement_json` 直接存结构化 requirement。
- 这是系统“可追溯”的核心。

### 4.5 `artifacts`

作用：挂在某次 run 下的结构化产物记录。

建议字段：

- `id`
- `run_id`
- `artifact_type` 例如 `OUTLINE` / `REVIEW` / `GATE`
- `version_no`
- `payload_json`
- `created_at`

说明：

- `outline.json`、`review.json`、`memory_gate.json` 可以直接存在这里的 JSONB 字段里。
- Phase 1 没必要为每种结构单独建一张表。

### 4.6 `character_cards`

作用：记录结构化人物卡。

建议字段：

- `id`
- `novel_id`
- `character_id`
- `canonical_name`
- `display_name`
- `aliases_json`
- `card_json`
- `merge_status`
- `created_at`
- `updated_at`

说明：

- `character_id` 是真正主键思路，不要只按名字合并。
- 复杂字段可以先放 JSONB。

### 4.7 `memory_deltas`

作用：记录一次 run 产出的待审批记忆更新。

建议字段：

- `id`
- `run_id`
- `novel_id`
- `delta_type` 例如 `CHARACTERS` / `WORLD_RULES` / `STORY_SO_FAR`
- `payload_json`
- `gate_status`
- `created_at`

说明：

- 先把 delta 当成待处理对象，而不是直接覆盖主记忆。

### 4.8 `merge_decisions`

作用：记录人工做出的角色合并/拆分/别名归并决策。

建议字段：

- `id`
- `novel_id`
- `run_id`
- `decision_type` 例如 `MERGE` / `SPLIT` / `ALIAS_LINK`
- `payload_json`
- `reason`
- `created_by`
- `created_at`

说明：

- 这是防止角色记忆污染的关键表。

---

## 5. 表关系怎么理解

可以先用下面这个简单关系图理解：

```text
novels
  └─ chapters
      └─ chapter_versions

novels
  └─ runs
      ├─ artifacts
      └─ memory_deltas

novels
  ├─ character_cards
  └─ merge_decisions
```

更直白一点：

- 一本小说有很多章节
- 一章有很多版本
- 一本小说会产生很多 run
- 一个 run 会产生很多结构化产物
- 角色卡属于某本小说，不属于某一章
- merge decision 是对角色系统的人工治理记录

---

## 6. Phase 1 最小字段设计建议

如果你还不熟数据库，不要一开始追求“完美第三范式”。

Phase 1 的正确策略是：

- 关系骨架先搭对
- 高频查询字段单独列出来
- 复杂结构先放 JSONB
- 等主链路稳定后再做拆表优化

比如：

- `review.json` 没必要一开始拆成 20 个字段
- `character_cards.card_json` 可以先包住复杂结构
- `artifacts.payload_json` 可以统一装 outline/review/gate

这会让你更快落地。

---

## 7. 实现步骤（给新手的顺序）

### 第一步：先建 Supabase 项目

你现在不用先自己装复杂数据库环境。最简单的方式是：

1. 建一个 Supabase 项目
2. 开启数据库和 Storage
3. 先不折腾 RLS 的高级玩法
4. 先跑通开发环境

### 第二步：先建最小表

优先级建议：

1. `novels`
2. `chapters`
3. `chapter_versions`
4. `runs`
5. `artifacts`

先把主链路跑起来，再补：

6. `character_cards`
7. `memory_deltas`
8. `merge_decisions`

### 第三步：在 API 层建立模型和 repository

推荐顺序：

1. 定义 SQLModel 或 SQLAlchemy 模型
2. 建 repository 层
3. 先写最小 CRUD
4. 再接入 run 工作流

### 第四步：把正文改成 Storage 引用

不要让 API 直接把正文塞进 `chapters` 表。

推荐流程：

1. 生成正文
2. 把正文写到 Storage
3. 返回 `storage_key`
4. 在 `chapter_versions` 里保存引用

### 第五步：把 run 主链路接到数据库

Phase 1 最重要的数据库接入顺序：

1. 创建 run
2. 更新 run 状态
3. 保存 artifact
4. 保存 chapter version 引用
5. 保存 memory delta
6. 保存 merge decision

---

## 8. 你现在最需要学的数据库知识

如果你完全没学过数据库，先只学这些就够：

1. 表（table）
2. 行（row）
3. 列（column）
4. 主键（primary key）
5. 外键（foreign key）
6. 一对多关系
7. JSONB 是什么
8. migration 是什么

你现在不需要先深挖：

- 复杂索引优化
- 分库分表
- 深入事务理论
- 高级 SQL 调优
- 复杂缓存架构

先会搭 Phase 1，就已经很够用了。

---

## 9. 推荐实现栈

### 对你当前项目最友好的方案

- DB：PostgreSQL
- 托管：Supabase
- Python ORM：`SQLModel`
- 迁移：`Alembic`

为什么是这个组合：

- Supabase 省去你很多环境成本
- SQLModel 比纯 SQLAlchemy 更容易上手
- Alembic 是标准迁移工具，后续可持续维护

---

## 10. Phase 1 数据库完成标准

数据库部分只有满足这些条件，才算达到 Phase 1 水平：

1. run 的状态、输入和产物可落库并可追溯。
2. 章节元数据和正文内容已经分离。
3. `outline/review/gate` 至少能稳定保存为结构化结果。
4. `characters` 不再只按名字做主键逻辑。
5. `memory delta` 和 `merge decision` 至少有落库模型。
6. API 不再依赖本地文件系统作为唯一真相来源。

---

## 11. 推荐下一步

数据库相关的实际推进顺序，我建议是：

1. 先确认这份 DB 方案
2. 再把它翻成实际表结构草案
3. 再把 `runs`、`chapters`、`artifacts` 三张表先实现
4. 再把 API 主链路接上
5. 最后再补角色和记忆治理相关表

如果后面继续推进，最合理的下一份文档应该是：

- `docs/DB_SCHEMA_DRAFT.md`

它可以把这份“易懂版计划”继续翻译成更接近真实建表的字段草案。
