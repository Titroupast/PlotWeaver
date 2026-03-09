# 7 天 MVP 精简版大纲

## 项目目标

在 7 天内做出一个 **轻小说续写 MVP**，验证下面这条最小闭环：

**最近正文 + 人设卡 + 少量剧情摘要 → 提纲 → 正文 → 审校结果**

## 非目标

这 7 天内先不做：

- 几百万字全文检索
- 复杂多 agent 协作
- 完整数据库 / 向量库
- 完整 skill 打包发布
- 生产级部署

------

## 第 1 天：跑通最小 API 调用

### 今天目标

先做一个最小脚本，能输入“前文 + 要求”，输出一段续写正文。

### 今天要做

- 写一个最小 API 调用脚本（先不抽工具、不做复杂封装）
- 输入（先用最小可行形态，支持硬编码或命令行传参）：
  - `novel_id`（用于决定输入/输出目录）
  - 最近一章正文 `prev_chapter`
  - 本章续写要求 `continuation_req`
- 输出：
  - 800–1200 字正文，保存到 `outputs/<novel_id>/draft_v1.txt`
- 把 prompt 分成两层：
  - `system`：文风、规则、禁忌（保持轻小说风格、避免重复）
  - `user`：本次续写任务（包含前文 + 续写要求）
- 最小运行流程：
  1. 读取/接收输入
  2. 组装 `system` + `user`
  3. 调用 API 得到正文
  4. 写入 `outputs/<novel_id>/draft_v1.txt`，并在控制台打印前几行做检查
- 基本健壮性：
  - `outputs/<novel_id>/` 不存在就创建
  - API 失败时给出清晰报错，不要静默失败

### 今天产出

- `app.py`
- `outputs/<novel_id>/draft_v1.txt`

### 完成标准

能稳定生成一章正文，不报错。

------

## 第 2 天：把“直接写”改成“先规划再写”

### 今天目标

让模型先输出章节提纲，再根据提纲写正文。

### 今天要做

先补一层“规划模型”，把“要写什么”写清楚：

- 新增 `planner` prompt（只产出 JSON，不写正文）
- JSON 严格约束为单一对象，不允许多余文本
- 如果 JSON 不合法：自动重试 1 次（或用一个“修复 JSON”的小提示）

定义一个简单 JSON 结构，例如：

```json
{
  "chapter_goal": "",
  "conflict": "",
  "beats": [],
  "foreshadowing": [],
  "ending_hook": ""
}
```

流程改成两步：

1. 先生成提纲 JSON（保存到 `outputs/<novel_id>/outline.json`）
2. 再根据提纲生成正文（保存到 `outputs/<novel_id>/draft_v2.txt`）

补充细节（确保能稳定跑通）：

- 生成提纲时输入：`prev_chapter` + `continuation_req` + 可选的风格约束
- 生成正文时输入：提纲 JSON + `prev_chapter`（避免跑偏）
- 加一个 `novel_id` 参数，确保不同小说写到不同目录

### 今天产出

- `outputs/<novel_id>/outline.json`
- `outputs/<novel_id>/draft_v2.txt`

### 完成标准

能稳定得到合法 JSON，并生成和提纲相符的正文。

------

## 第 3 天：加轻量记忆，不上重型检索

### 今天目标

先解决“角色失忆、设定冲突”，但先不用向量库。

### 今天要做

准备 3 个轻量文件（按小说分目录）：

- `inputs/<novel_id>/characters.json`
- `inputs/<novel_id>/world_rules.md`
- `inputs/<novel_id>/story_so_far.md`

先用最简单的方法把相关信息喂给模型：

- 手动挑选相关设定
- 或用关键词匹配选 2–5 条相关摘要

### 今天产出

- 一份基础人设卡
- 一份剧情摘要
- 一版带记忆输入的续写流程

### 完成标准

模型生成时能参考人设和设定，不再只靠最近正文硬写。

> 这一步是对你原来第 3 天的缩小版。原稿里是直接做 File search / 可检索知识库，这长期是对的，但对 7 天 MVP 来说偏重。

------

## 第 4 天：加最小工具调用闭环

### 今天目标

让模型不只是写，还能调用你提供的简单函数。

### 今天要做

先只准备 2 到 3 个最小函数：

- `get_character_profile(name)`
- `get_story_summary(topic)`
- `save_chapter_draft(text)`

要求至少跑通一次完整流程：

1. 取角色设定
2. 生成提纲或正文
3. 保存草稿

### 今天产出

- `tools.py`
- `outputs/<novel_id>/run_log.json`
- `outputs/<novel_id>/draft_v3.txt`

### 完成标准

至少有一次真实工具调用日志，不只是写了函数定义。

> 你原稿第 4 天的方向很好，建议只是把“成功标准”再写死一点。

------

## 第 5 天：做一个基础审校器

### 今天目标

让系统写完后能给出结构化问题报告。

### 今天要做

定义一个审校输出结构，例如：

```json
{
  "character_consistency_score": 0,
  "world_consistency_score": 0,
  "style_match_score": 0,
  "repetition_issues": [],
  "revision_suggestions": []
}
```

输入：

- 本章正文
- 人设摘要
- 世界设定摘要

输出：

- 评分
- 问题
- 修改建议

### 今天产出

- `outputs/<novel_id>/review.json`

### 完成标准

能对同一章输出较稳定的审校报告。

------

## 第 6 天：增量记忆与闸门

### 今天目标

建立“增量记忆更新 + 质量闸门”的机制，避免每次全量重建记忆造成耗费与污染。

### 前置条件

第 5 天的审校器完成后，才能启用“模型审校自动闸门”。

### 今天要做

1. 增量记忆更新
   - 仅对**新生成的章节**提取候选记忆（characters / world_rules / story_so_far 的 delta）
   - 先写入 `memory/updates/` 作为候选，不直接覆盖主记忆
2. 质量闸门（依赖 Day5 审校器）
   - 审校分数/问题通过阈值才允许合并
   - 未通过则保留候选文件但不合并
3. 合并策略
   - 通过闸门后，将 delta 合并进主记忆文件
   - 保留合并记录，方便回溯

### 今天产出

- `memory/updates/characters_delta.json`
- `memory/updates/world_rules_delta.md`
- `memory/updates/story_so_far_delta.md`
- 一份“闸门规则”文档（阈值与合并规则）

### 完成标准

能在不全量重建的前提下，安全地更新记忆；不合格章节不会污染主记忆。

------

## 第 7 天：做最小评测集

### 今天目标

不要只“感觉变好了”，要开始留测试基线。

### 今天要做

准备 10 组小样本，每组包含：

- 前文摘要
- 本章要求
- 关键设定

每次运行后记录：

- 人设是否一致
- 是否吃书
- 是否有剧情推进
- 是否有 hook
- 总分

再额外补 2–3 条你自己觉得“写得对味”的人工参考样本。

### 今天产出

- `evals/<novel_id>/test_cases.json`
- `evals/<novel_id>/results.csv`

### 完成标准

你能拿同一个版本反复跑，并比较结果。

> 你原稿第 7 天本来就很重要，我只建议再补一个“人工参考样本”。



# 1. 项目目录结构

```text
project/
  app.py
  tools.py
  prompts/
    planner.txt
    writer.txt
    reviewer.txt
  inputs/
    <novel_id>/
      prev_chapter.md
      continuation_req.md
      characters.json
      world_rules.md
      story_so_far.md
  outputs/
    <novel_id>/
      outline.json
      draft_v1.txt
      draft_v2.txt
      review.json
      run_log.json
  skills/
    outline-planner.md
  evals/
    <novel_id>/
      test_cases.json
      results.csv
```

# 2. 最终验收标准

建议直接加一个 checklist：

- 能成功调用 API 生成一章正文
- 能先生成提纲，再生成正文
- 能读取基础设定文件
- 能完成至少一次工具调用闭环
- 能输出结构化审校结果
- 能保存至少 10 条测试结果
- 能沉淀 1 个完整的 skill 草稿

