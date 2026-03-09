# Day 4 使用指南（工具调用闭环）

本目录在 Day3 基础上加入了最小工具调用闭环，并按章节目录输出结果。

---

## 1. 环境准备

```bash
pip install -r requirements.txt
```

配置 `.env`（与 Day1/Day2 一致）：

```
ARK_API_KEY=your_key
ARK_MODEL=your_model_id
```

可选：
```
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

---

## 2. 输入目录结构

```
inputs/
  demo/
    chapters/
      chapter_001/
        chapter.txt
        title.txt
      chapter_002/
        chapter.txt
        title.txt
      ...
    memory/
      characters.json
      world_rules.md
      story_so_far.md
```

说明：
- `chapter.txt` 为章节正文。
- `title.txt` 为章节标题。
- `memory/` 下三份文件会被注入到模型作为记忆信息。

---

## 3. 续写要求（Prompt）

默认续写要求放在：
```
prompts/continuation_req.txt
```

如需自定义，可在运行时传入：
```
--req path/to/custom_req.txt
```

---

## 4. 刷新记忆文件（可选）

如果你希望根据**全部章节**重新生成三份记忆文件：

```bash
python app.py --novel-id demo --chapter-id chapter_004 --refresh-memory
```

此操作会调用模型并写入：
```
inputs/demo/memory/characters.json
inputs/demo/memory/world_rules.md
inputs/demo/memory/story_so_far.md
```

---

## 5. 生成提纲 + 续写正文

按章节运行：

```bash
python app.py --novel-id demo --chapter-id chapter_004
```

---

## 6. 输出结构

```
outputs/
  demo/
    run_log.json
    chapters/
      chapter_005/
        outline.json
        chapter.txt
        title.txt
```

说明：
- `outline.json`：本章提纲
- `chapter.txt`：本章正文（第一行为标题）
- `title.txt`：本章标题
- `run_log.json`：工具调用日志

---

## 7. 工具调用说明

Day4 内置 4 个工具函数：

- `build_characters()` → 生成 `characters.json`
- `build_world_rules()` → 生成 `world_rules.md`
- `build_story_so_far()` → 生成 `story_so_far.md`
- `save_chapter_draft()` → 保存草稿到 outputs，并写入日志

使用 `--refresh-memory` 时会调用前三个工具。

---

## 8. 常用命令汇总

```bash
# 只生成提纲+正文
python app.py --novel-id demo --chapter-id chapter_004

# 先刷新记忆，再生成提纲+正文
python app.py --novel-id demo --chapter-id chapter_004 --refresh-memory

# 仅刷新记忆并退出
python app.py --novel-id demo --refresh-memory --only-refresh-memory
```
