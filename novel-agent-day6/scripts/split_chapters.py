import argparse
import re
from pathlib import Path


CHAPTER_RE = re.compile(r"^##\s*第\s*([0-9一二三四五六七八九十百千]+)\s*章[:：]?\s*(.*)$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve_input_path(raw_path: Path) -> Path:
    if raw_path.exists():
        return raw_path

    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / raw_path,
        script_dir.parent / raw_path,
        script_dir.parent.parent / raw_path,
        script_dir.parent.parent.parent / raw_path,
        script_dir.parent / "inputs" / "demo" / raw_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"No such file: {raw_path}")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_chinese_numeral(text: str) -> int:
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}

    total = 0
    current = 0
    for char in text:
        if char in digits:
            current = digits[char]
        elif char in units:
            unit = units[char]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
        else:
            return 0
    return total + current


def split_chapters(markdown: str):
    lines = markdown.splitlines()
    chapters = []
    current_title = None
    current_lines = []
    current_num = None

    for line in lines:
        match = CHAPTER_RE.match(line.strip())
        if match:
            if current_title:
                chapters.append((current_num, current_title, "\n".join(current_lines).strip()))
            raw_num = match.group(1)
            try:
                current_num = int(raw_num)
            except ValueError:
                current_num = parse_chinese_numeral(raw_num)
                if current_num <= 0:
                    current_num = None
            title_suffix = match.group(2).strip()
            current_title = f"第{current_num}章"
            if title_suffix:
                current_title = f"{current_title}：{title_suffix}"
            current_lines = [line]
        else:
            if current_title is not None:
                current_lines.append(line)

    if current_title:
        chapters.append((current_num, current_title, "\n".join(current_lines).strip()))

    return chapters


def main() -> None:
    parser = argparse.ArgumentParser(description="Split novel markdown into chapter folders.")
    parser.add_argument("--input", required=True, type=Path, help="Novel markdown file.")
    parser.add_argument("--novel-id", default="demo", help="Novel identifier.")
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "inputs" / "demo",
        help="Inputs root directory.",
    )
    args = parser.parse_args()

    input_path = resolve_input_path(args.input)
    content = read_text(input_path)
    chapters = split_chapters(content)
    if not chapters:
        raise ValueError("No chapter headings found. Expected lines like '## 第1章：标题'.")

    if args.out_root.name == "demo" and args.novel_id == "demo":
        novel_dir = args.out_root / "chapters"
    else:
        novel_dir = args.out_root / args.novel_id / "chapters"
    for idx, (num, title, body) in enumerate(chapters, start=1):
        folder_num = num if isinstance(num, int) else idx
        folder = novel_dir / f"chapter_{folder_num:03d}"
        write_text(folder / "chapter.txt", body)
        write_text(folder / "title.txt", title)

    index_lines = []
    for idx, (num, title, _) in enumerate(chapters, start=1):
        folder_num = num if isinstance(num, int) else idx
        index_lines.append(f"{folder_num:03d}\t{title}")
    write_text(novel_dir / "index.txt", "\n".join(index_lines))


if __name__ == "__main__":
    main()
