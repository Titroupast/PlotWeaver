# Day 4 工作总结

本次在 Day3 基础上完成了最小工具调用闭环，并按“章节目录”组织输入/输出。

## 已完成内容

1. 工具调用闭环
   - 新增 `tools.py`
   - 实现 4 个工具函数：
     - `build_characters()`：基于全部章节生成 `characters.json`
     - `build_world_rules()`：基于全部章节生成 `world_rules.md`
     - `build_story_so_far()`：基于全部章节生成 `story_so_far.md`
     - `save_chapter_draft()`：保存草稿到 outputs 并记录日志
   - 输出工具调用日志：`outputs/<novel_id>/run_log.json`

2. 章节级输出
   - 运行 `--chapter-id chapter_004` 时：
     - 自动将新章写回 `inputs/<novel_id>/chapters/chapter_005/`
     - 同时在 `outputs/<novel_id>/chapters/chapter_005/` 生成：
       - `outline.json`
       - `chapter.txt`
       - `title.txt`
   - `inputs/.../chapters/index.txt` 自动追加并标注 `(generated)`

3. 记忆文件刷新机制
   - 支持 `--refresh-memory` 从全部章节重建记忆文件
   - 支持 `--only-refresh-memory` 仅刷新记忆并退出

## 当前目录结构（关键部分）

```
inputs/<novel_id>/
  chapters/
    chapter_001/
      chapter.txt
      title.txt
    chapter_005/
      chapter.txt
      title.txt
      output.txt
    index.txt
  memory/
    characters.json
    world_rules.md
    story_so_far.md

outputs/<novel_id>/
  run_log.json
  chapters/
    chapter_005/
      outline.json
      chapter.txt
      title.txt
```

