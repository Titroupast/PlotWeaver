# Day 6 浣跨敤鎸囧崡锛堝閲忚蹇嗕笌闂搁棬锛?
鏈洰褰曞湪 Day5 鍩虹涓婂姞鍏モ€滃閲忚蹇嗘洿鏂?+ 璐ㄩ噺闂搁棬鈥濄€?
---

## 1. 鐜鍑嗗

```bash
pip install -r requirements.txt
```

閰嶇疆 `.env`锛堜笌 Day1/Day2 涓€鑷达級锛?
```
ARK_API_KEY=your_key
ARK_MODEL=your_model_id
```

鍙€夛細
```
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

---

## 2. 输入目录结构

注意：当前 Day6 样例数据主要使用 `chapter.txt` + `title.txt`；`chapter_meta.json` 为 Phase 1 规划产物（见仓库根目录 `SPEC.md` 的 6.8），因此在样例中可能缺省。

```
inputs/
  demo/
    chapters/
      chapter_001/
        chapter.txt
        chapter_meta.json        (Phase 1 新增；当前可缺省)
        title.txt        (可选兼容：由 chapter_meta.json 派生)
      chapter_002/
        chapter.txt
        chapter_meta.json        (Phase 1 新增；当前可缺省)
        title.txt        (可选兼容：由 chapter_meta.json 派生)
      ...
    memory/
      characters.json
      world_rules.md
      story_so_far.md
```

语义约定：
- `chapter.txt`：章节正文（仅正文内容，不包含标题行）。
- `chapter_meta.json`：Phase 1 起新增的章节元数据（标题/副标题/类型/排序/摘要等；权威来源）。若缺失（Day6 样例现状），以 `title.txt` 作为最小兼容（不从正文推断标题）。
- `title.txt`：当前 Day6 样例使用的标题文件；Phase 1 引入 `chapter_meta.json` 后可由其派生生成（仅作兼容/缓存）。
- `memory/`：主记忆材料。
---

## 3. 缁啓瑕佹眰锛圥rompt锛?
榛樿缁啓瑕佹眰鏀惧湪锛?```
prompts/continuation_req.txt
```

濡傞渶鑷畾涔夛紝鍙湪杩愯鏃朵紶鍏ワ細
```
--req path/to/custom_req.txt
```

---

## 4. 鍒锋柊璁板繂鏂囦欢锛堝彲閫夛級

濡傛灉浣犲笇鏈涙牴鎹?*鍏ㄩ儴绔犺妭**閲嶆柊鐢熸垚涓変唤璁板繂鏂囦欢锛?
```bash
python app.py --novel-id demo --chapter-id chapter_004 --refresh-memory
```

姝ゆ搷浣滀細璋冪敤妯″瀷骞跺啓鍏ワ細
```
inputs/demo/memory/characters.json
inputs/demo/memory/world_rules.md
inputs/demo/memory/story_so_far.md
```

---

## 5. 鐢熸垚鎻愮翰 + 缁啓姝ｆ枃

鎸夌珷鑺傝繍琛岋細

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
        chapter_meta.json        (Phase 1 新增；当前可缺省)
        title.txt        (可选兼容：由 chapter_meta.json 派生)
        review.json
        memory_gate.json
```

语义约定：
- Phase 1 起：`chapter_meta.json` 是标题/类型/摘要等元数据的权威来源；UI 与索引不依赖正文第一行。若缺失则以 `title.txt` 兼容。
- `chapter.txt` 仅保存正文内容。
---

## 7. 宸ュ叿璋冪敤璇存槑

Day4 鍐呯疆 4 涓伐鍏峰嚱鏁帮細

- `build_characters()` 鈫?鐢熸垚 `characters.json`
- `build_world_rules()` 鈫?鐢熸垚 `world_rules.md`
- `build_story_so_far()` 鈫?鐢熸垚 `story_so_far.md`
- `save_chapter_draft()` 鈫?淇濆瓨鑽夌鍒?outputs锛屽苟鍐欏叆鏃ュ織

浣跨敤 `--refresh-memory` 鏃朵細璋冪敤鍓嶄笁涓伐鍏枫€?
---

## 8. 甯哥敤鍛戒护姹囨€?
```bash
# 鍙敓鎴愭彁绾?姝ｆ枃
python app.py --novel-id demo --chapter-id chapter_004

# 鍏堝埛鏂拌蹇嗭紝鍐嶇敓鎴愭彁绾?姝ｆ枃
python app.py --novel-id demo --chapter-id chapter_004 --refresh-memory

# 浠呭埛鏂拌蹇嗗苟閫€鍑?python app.py --novel-id demo --refresh-memory --only-refresh-memory

# 鐢熸垚绔犺妭 + 澧為噺璁板繂 + 闂搁棬鍚堝苟
python app.py --novel-id demo --chapter-id chapter_004 --update-memory
```
