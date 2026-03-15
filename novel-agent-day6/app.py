from __future__ import annotations

import argparse
import json
import re
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from openai import OpenAI

from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL
from prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_TEMPLATE,
    REVIEWER_SYSTEM_PROMPT,
    REVIEWER_USER_TEMPLATE,
    WRITER_SYSTEM_PROMPT,
    WRITER_USER_TEMPLATE,
)
from tools import ToolRunner
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts.io import (
    chapter_meta_from_title_compat,
    load_characters_contract,
    normalize_memory_gate_from_review,
    write_chapter_meta_contract,
    write_characters_contract,
    write_memory_gate_contract,
    write_outline_contract,
    write_review_contract,
)

BASE_DIR = Path(__file__).parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"

PLANNER_TEMPERATURE = 0.2
WRITER_TEMPERATURE = 0.7


def build_client() -> OpenAI:
    return OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def call_chat(
    client: OpenAI, system_prompt: str, user_prompt: str, temperature: float
) -> str:
    resp = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def generate_outline(
    client: OpenAI,
    previous_chapter: str,
    requirements: str,
    memory_context: str,
    style_constraints: str,
    max_retry: int = 1,
) -> Dict[str, Any]:
    user_prompt = PLANNER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        requirements=requirements.strip(),
        memory_context=memory_context.strip() or "",
        style_constraints=style_constraints.strip() or "",
    )

    last_text = ""
    attempts = 1 + max_retry
    for attempt in range(attempts):
        if attempt == 0:
            response = call_chat(
                client, PLANNER_SYSTEM_PROMPT, user_prompt, PLANNER_TEMPERATURE
            )
        else:
            fix_prompt = (
                "The previous output was not valid JSON. Please output ONLY a valid JSON object.\n\n"
                f"Previous output:\n{last_text}"
            )
            response = call_chat(client, PLANNER_SYSTEM_PROMPT, fix_prompt, 0.0)

        last_text = response
        try:
            payload = extract_json_object(response)
            return json.loads(payload)
        except json.JSONDecodeError:
            continue

    raise ValueError("Failed to produce valid JSON outline after retry.")


def generate_draft(
    client: OpenAI,
    previous_chapter: str,
    outline: Dict[str, Any],
    memory_context: str,
) -> str:
    outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
    user_prompt = WRITER_USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        outline_json=outline_json,
        memory_context=memory_context.strip() or "",
    )
    return call_chat(client, WRITER_SYSTEM_PROMPT, user_prompt, WRITER_TEMPERATURE)


def generate_review(
    client: OpenAI,
    chapter_text: str,
    character_summary: str,
    world_summary: str,
    requirement_context: Dict[str, Any],
    chapter_meta: Dict[str, Any],
    max_retry: int = 1,
) -> Dict[str, Any]:
    user_prompt = REVIEWER_USER_TEMPLATE.format(
        chapter_text=chapter_text.strip(),
        character_summary=character_summary.strip() or "",
        world_summary=world_summary.strip() or "",
    )
    user_prompt = (
        f"{user_prompt}\n\n"
        "[Structured continuation requirement JSON]\n"
        f"{json.dumps(requirement_context, ensure_ascii=False, indent=2)}\n\n"
        "[Chapter meta JSON]\n"
        f"{json.dumps(chapter_meta, ensure_ascii=False, indent=2)}"
    )
    last_text = ""
    attempts = 1 + max_retry
    for attempt in range(attempts):
        if attempt == 0:
            response = call_chat(client, REVIEWER_SYSTEM_PROMPT, user_prompt, 0.2)
        else:
            fix_prompt = (
                "The previous output was not valid JSON. Please output ONLY a valid JSON object.\n\n"
                f"Previous output:\n{last_text}"
            )
            response = call_chat(client, REVIEWER_SYSTEM_PROMPT, fix_prompt, 0.0)

        last_text = response
        try:
            payload = extract_json_object(response)
            return json.loads(payload)
        except json.JSONDecodeError:
            continue

    raise ValueError("Failed to produce valid review JSON after retry.")


def resolve_input_path(novel_id: str, provided: Optional[Path], filename: str) -> Path:
    if provided is not None:
        return provided
    return INPUTS_DIR / novel_id / filename


def resolve_chapter_path(
    novel_id: str, chapter_id: Optional[str], provided: Optional[Path]
) -> Optional[Path]:
    if provided is not None:
        return provided
    if chapter_id is None:
        return None
    return INPUTS_DIR / novel_id / "chapters" / chapter_id / "chapter.txt"


def resolve_chapter_req_path(novel_id: str, chapter_id: Optional[str]) -> Optional[Path]:
    if chapter_id is None:
        return None
    return INPUTS_DIR / novel_id / "chapters" / chapter_id / "continuation_req.txt"


def extract_keywords(text: str, limit: int = 8) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    stopwords = set()
    counts: Dict[str, int] = {}
    for token in tokens:
        if token in stopwords:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    return [item[0] for item in ranked[:limit]]


def next_chapter_id(chapter_id: str) -> Optional[str]:
    match = re.match(r"chapter_(\d+)$", chapter_id)
    if not match:
        return None
    number = int(match.group(1)) + 1
    return f"chapter_{number:03d}"


def split_title_and_body(text: str) -> Dict[str, str]:
    lines = text.strip().splitlines()
    if not lines:
        return {"title": "## Untitled", "body": text.strip()}
    title = lines[0].strip()
    if not title.startswith("## "):
        title = f"## {title}"
    # Body must not include the title line (decouple metadata from body text).
    body = "\n".join(lines[1:]).lstrip("\n").rstrip()
    return {"title": title, "body": body}


def parse_requirement_context(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    default_req = {
        "chapter_goal": "",
        "must_include": [],
        "must_not_include": [],
        "tone": {"style": "", "pov": "第三人称有限", "language": "中文", "tags": []},
        "continuity_constraints": [],
        "target_length": {"unit": "字", "min": 1800, "max": 2400},
        "optional_notes": "",
    }
    if not text:
        return default_req
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                merged = dict(default_req)
                merged.update(data)
                return merged
        except json.JSONDecodeError:
            pass
    default_req["optional_notes"] = text
    return default_req


def build_summary_from_body(body: str, max_len: int = 120) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def update_index(index_path: Path, chapter_id: str, title: str, generated: bool = True) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    title_clean = title.replace("##", "").strip()
    suffix = " (generated)" if generated else ""
    line = f"{chapter_id.replace('chapter_', '')}\t{title_clean}{suffix}"

    lines = []
    if index_path.exists():
        lines = [ln.rstrip("\n") for ln in index_path.read_text(encoding="utf-8").splitlines()]

    # Avoid duplicates for the same chapter id
    updated = []
    replaced = False
    for ln in lines:
        if ln.startswith(chapter_id.replace("chapter_", "")):
            updated.append(line)
            replaced = True
        else:
            updated.append(ln)
    if not replaced:
        updated.append(line)

    index_path.write_text("\n".join(updated).strip() + "\n", encoding="utf-8")


def pick_lines_by_keywords(lines: Iterable[str], keywords: List[str], limit: int) -> List[str]:
    picked = []
    for line in lines:
        if any(keyword in line for keyword in keywords):
            picked.append(line.strip())
        if len(picked) >= limit:
            break
    return picked


def summarize_characters(characters_path: Path, keywords: List[str]) -> List[str]:
    if not characters_path.exists():
        return []
    data = load_characters_contract(characters_path)
    characters = data.get("characters", [])
    results: List[str] = []
    for entry in characters:
        name = entry.get("display_name") or entry.get("canonical_name") or entry.get("name", "")
        role = entry.get("role", "")
        cid = entry.get("character_id") or ""
        aliases = entry.get("aliases") or []
        alias_str = ""
        if aliases:
            alias_str = " (aliases: " + ", ".join([str(a) for a in aliases[:3] if a]) + ")"
        summary = f"{name} ({role}) {cid}{alias_str}".strip()
        serialized = json.dumps(entry, ensure_ascii=False)
        if not keywords or any(keyword in serialized for keyword in keywords):
            results.append(summary)
    return results[:6]

def build_review_context(memory_dir: Path) -> Dict[str, str]:
    characters_path = memory_dir / "characters.json"
    world_path = memory_dir / "world_rules.md"

    character_lines: List[str] = []
    if characters_path.exists():
        data = load_characters_contract(characters_path)
        for entry in data.get("characters", []) or []:
            if not isinstance(entry, dict):
                continue
            name = entry.get("display_name") or entry.get("canonical_name") or entry.get("name", "")
            role = entry.get("role", "")
            if name:
                character_lines.append(f"{name} ({role})".strip())

    world_lines: List[str] = []
    if world_path.exists():
        world_lines = [line.strip() for line in world_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    return {
        "character_summary": "\n".join(character_lines[:8]),
        "world_summary": "\n".join(world_lines[:8]),
    }


def evaluate_gate(review: Dict[str, Any], min_score: int, max_repetition: int) -> Dict[str, Any]:
    issues = []
    for key in ("character_consistency_score", "world_consistency_score", "style_match_score"):
        if int(review.get(key, 0)) < min_score:
            issues.append(f"{key}<{min_score}")
    repetition_count = len(review.get("repetition_issues", []) or [])
    if repetition_count > max_repetition:
        issues.append(f"repetition_issues>{max_repetition}")
    return {"pass": len(issues) == 0, "issues": issues}


def merge_list_lines(base_lines: List[str], delta_lines: List[str]) -> List[str]:
    existing = {line.strip() for line in base_lines if line.strip()}
    merged = list(base_lines)
    for line in delta_lines:
        clean = line.strip()
        if clean and clean not in existing:
            merged.append(clean)
            existing.add(clean)
    return merged


def normalize_ordered_list(lines: List[str]) -> List[str]:
    stripped = []
    for line in lines:
        clean = re.sub(r"^\s*\d+\.\s*", "", line.strip())
        if clean:
            stripped.append(clean)
    return [f"{idx}. {item}" for idx, item in enumerate(stripped, start=1)]


def merge_world_rules(base_path: Path, delta_path: Path, max_items: int = 20) -> None:
    if not delta_path.exists():
        return
    base_lines = base_path.read_text(encoding="utf-8").splitlines() if base_path.exists() else []
    delta_lines = delta_path.read_text(encoding="utf-8").splitlines()
    merged = merge_list_lines(base_lines, delta_lines)
    normalized = normalize_ordered_list(merged)[:max_items]
    base_path.write_text("\n".join(normalized).strip() + "\n", encoding="utf-8")


def merge_story_so_far(base_path: Path, delta_path: Path, max_items: int = 30) -> None:
    if not delta_path.exists():
        return
    base_lines = base_path.read_text(encoding="utf-8").splitlines() if base_path.exists() else []
    delta_lines = delta_path.read_text(encoding="utf-8").splitlines()
    merged = merge_list_lines(base_lines, delta_lines)
    normalized = normalize_ordered_list(merged)[:max_items]
    base_path.write_text("\n".join(normalized).strip() + "\n", encoding="utf-8")


def _stable_legacy_character_id(entry: Dict[str, Any]) -> str:
    """Best-effort stable id for legacy character cards (migration aid for Day6)."""
    existing = (entry.get("character_id") or "").strip()
    if existing:
        return existing
    canonical = (
        (entry.get("canonical_name") or "").strip()
        or (entry.get("display_name") or "").strip()
        or (entry.get("name") or "").strip()
    )
    role = (entry.get("role") or "").strip()
    age = entry.get("age")
    age_str = "" if age is None else str(age)
    key = f"{canonical}|{role}|{age_str}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"char_legacy_{digest}"


def _normalize_character_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    if "canonical_name" not in entry and entry.get("name"):
        entry["canonical_name"] = entry.get("name")
    if "display_name" not in entry and entry.get("canonical_name"):
        entry["display_name"] = entry.get("canonical_name")
    if "aliases" not in entry or entry.get("aliases") is None:
        entry["aliases"] = []
    entry["character_id"] = _stable_legacy_character_id(entry)
    return entry


def _merge_value_into_target(target: Dict[str, Any], key: str, value: Any) -> None:
    if key in {"character_id"} or value is None:
        return
    if isinstance(value, list):
        existing = target.get(key) or []
        if not isinstance(existing, list):
            existing = []
        seen = set(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in existing)
        for item in value:
            sig = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if sig not in seen:
                existing.append(item)
                seen.add(sig)
        target[key] = existing
        return
    if isinstance(value, dict):
        existing = target.get(key) or {}
        if not isinstance(existing, dict):
            existing = {}
        existing.update(value)
        target[key] = existing
        return
    if value and not target.get(key):
        target[key] = value


def _match_character_candidates(base_chars: List[Dict[str, Any]], canonical_name: str, aliases: List[str]) -> List[Dict[str, Any]]:
    canonical_name = (canonical_name or "").strip()
    aliases = [a.strip() for a in (aliases or []) if a and a.strip()]
    scored: List[tuple[int, Dict[str, Any]]] = []
    for c in base_chars:
        score = 0
        base_canonical = (c.get("canonical_name") or c.get("name") or "").strip()
        if canonical_name and canonical_name == base_canonical:
            score += 2
        base_aliases = set((c.get("aliases") or []))
        score += len(base_aliases.intersection(aliases))
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def merge_characters(base_path: Path, delta_path: Path) -> None:
    if not delta_path.exists():
        return
    try:
        delta_data = json.loads(delta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    base_data: Dict[str, Any] = {"characters": []}
    if base_path.exists():
        try:
            base_data = json.loads(base_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            base_data = {"characters": []}

    base_list: List[Dict[str, Any]] = []
    for c in base_data.get("characters", []) or []:
        if isinstance(c, dict):
            base_list.append(_normalize_character_entry(c))
    base_by_id = {c.get("character_id"): c for c in base_list if c.get("character_id")}

    pending_review: List[Dict[str, Any]] = []
    for raw in delta_data.get("characters", []) or []:
        if not isinstance(raw, dict):
            continue
        entry = dict(raw)
        cid = entry.get("character_id")
        if isinstance(cid, str) and cid.strip():
            cid = cid.strip()
        else:
            cid = None
        canonical_name = (entry.get("canonical_name") or entry.get("name") or "").strip()
        aliases = entry.get("aliases") or []

        if cid and cid in base_by_id:
            target = base_by_id[cid]
            for k, v in entry.items():
                _merge_value_into_target(target, k, v)
            continue

        candidates = _match_character_candidates(base_list, canonical_name, aliases)
        if len(candidates) == 1:
            target = candidates[0]
            for k, v in entry.items():
                _merge_value_into_target(target, k, v)
            continue

        # Ambiguous or no match -> do not auto-merge.
        entry["character_id"] = cid
        entry.setdefault("merge_status", "PENDING_REVIEW")
        pending_review.append(entry)

    base_data["characters"] = base_list
    write_characters_contract(base_path, base_data, strict=False)

    if pending_review:
        pending_path = delta_path.parent / "characters_pending_review.json"
        write_characters_contract(pending_path, {"characters": pending_review}, strict=False)

def build_memory_context(
    memory_dir: Path,
    previous_chapter: str,
    requirements: str,
    tool_runner: ToolRunner,
) -> str:
    keywords = extract_keywords(previous_chapter + "\n" + requirements)

    characters_path = memory_dir / "characters.json"
    world_path = memory_dir / "world_rules.md"
    story_path = memory_dir / "story_so_far.md"

    # Fact layer (structured): mainly characters in Phase 1
    character_lines = summarize_characters(characters_path, keywords)

    # Summary layer (compressed): world + story snippets
    world_lines: List[str] = []
    story_lines: List[str] = []
    if world_path.exists():
        world_lines = pick_lines_by_keywords(
            [line for line in world_path.read_text(encoding="utf-8").splitlines() if line.strip()],
            keywords,
            limit=5,
        )
    if story_path.exists():
        story_lines = pick_lines_by_keywords(
            [line for line in story_path.read_text(encoding="utf-8").splitlines() if line.strip()],
            keywords,
            limit=5,
        )

    sections: List[str] = []
    if character_lines:
        sections.append("[FACT] Characters\n" + "\n".join(f"- {ln}" for ln in character_lines))
    if world_lines:
        sections.append("[SUMMARY] World Rules\n" + "\n".join(f"- {ln}" for ln in world_lines))
    if story_lines:
        sections.append("[SUMMARY] Story So Far\n" + "\n".join(f"- {ln}" for ln in story_lines))

    if sections:
        sections.append("[PROMPT] Assemble context for this run (facts + summaries + requirement + previous chapter)")
        return "\n\n".join(sections)
    return ""

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Day 6: incremental memory + gate.")
    parser.add_argument("--novel-id", default="demo", help="Novel identifier.")
    parser.add_argument("--prev", type=Path, help="Path to prev_chapter.txt.")
    parser.add_argument("--req", type=Path, help="Path to continuation_req.txt.")
    parser.add_argument("--style", type=Path, help="Optional style constraints file.")
    parser.add_argument("--chapter-id", help="Use inputs/<novel_id>/chapters/<id>/chapter.txt.")
    parser.add_argument("--max-retry", type=int, default=1, help="JSON retry count.")
    parser.add_argument("--refresh-memory", action="store_true", help="Rebuild memory files from chapters.")
    parser.add_argument(
        "--only-refresh-memory",
        action="store_true",
        help="Only rebuild memory files and exit.",
    )
    parser.add_argument("--update-memory", action="store_true", help="Build delta memory and gate merge.")
    parser.add_argument("--gate-min-score", type=int, default=70, help="Min score for review gate.")
    parser.add_argument("--gate-max-repetition", type=int, default=2, help="Max repetition issues allowed.")
    parser.add_argument(
        "--retry-with-review",
        action="store_true",
        help="Append last review issues/suggestions into requirements.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    novel_id = args.novel_id

    prev_path = resolve_input_path(novel_id, args.prev, "prev_chapter.txt")
    req_path = args.req if args.req is not None else (BASE_DIR / "prompts" / "continuation_req.txt")
    chapter_path = resolve_chapter_path(novel_id, args.chapter_id, None)
    style_path = args.style

    if chapter_path is not None:
        prev_path = chapter_path

    memory_dir = INPUTS_DIR / novel_id / "memory"
    run_log_path = OUTPUTS_DIR / novel_id / "run_log.json"
    tool_runner = ToolRunner(
        build_client(),
        ARK_MODEL,
        memory_dir,
        run_log_path,
        BASE_DIR / "prompts",
        OUTPUTS_DIR / novel_id,
    )

    if args.refresh_memory:
        chapters_root = INPUTS_DIR / novel_id / "chapters"
        chapter_files = sorted(chapters_root.glob("chapter_*/chapter.txt"))
        chapters_text = "\n\n".join(read_text(path) for path in chapter_files)
        if chapters_text:
            tool_runner.build_characters(chapters_text)
            tool_runner.build_world_rules(chapters_text)
            tool_runner.build_story_so_far(chapters_text)

    if args.only_refresh_memory:
        tool_runner.flush()
        print("[Info] Memory refreshed. Exiting as requested.")
        return

    if not prev_path.exists():
        raise FileNotFoundError(f"Missing prev_chapter file: {prev_path}")
    if not req_path.exists():
        raise FileNotFoundError(f"Missing continuation_req file: {req_path}")
    if style_path and not style_path.exists():
        raise FileNotFoundError(f"Missing style constraints file: {style_path}")

    previous_chapter = read_text(prev_path)
    requirements = read_text(req_path)
    style_constraints = read_text(style_path) if style_path else ""


    memory_context = build_memory_context(memory_dir, previous_chapter, requirements, tool_runner)

    client = build_client()

    if args.retry_with_review and args.chapter_id:
        last_review_path = OUTPUTS_DIR / novel_id / "chapters" / args.chapter_id / "review.json"
        if last_review_path.exists():
            try:
                review_data = json.loads(last_review_path.read_text(encoding="utf-8"))
                issues = review_data.get("repetition_issues", []) or []
                suggestions = review_data.get("revision_suggestions", []) or []
                summary_lines = []
                if issues:
                    summary_lines.append("[Last review issues]")
                    summary_lines.extend([f"- {item}" for item in issues[:5]])
                if suggestions:
                    summary_lines.append("[Last review suggestions]")
                    summary_lines.extend([f"- {item}" for item in suggestions[:5]])
                if summary_lines:
                    requirements = requirements.strip() + "\n\n[Last review summary]\n" + "\n".join(summary_lines)
            except json.JSONDecodeError:
                pass

    outline = generate_outline(
        client,
        previous_chapter,
        requirements,
        memory_context,
        style_constraints,
        max_retry=args.max_retry,
    )
    next_id = next_chapter_id(args.chapter_id) if args.chapter_id else None
    if next_id:
        output_dir = OUTPUTS_DIR / novel_id / "chapters" / next_id
    elif args.chapter_id:
        output_dir = OUTPUTS_DIR / novel_id / "chapters" / args.chapter_id
    else:
        output_dir = OUTPUTS_DIR / novel_id

    outline_path = output_dir / "outline.json"
    outline = write_outline_contract(outline_path, outline)

    draft = generate_draft(client, previous_chapter, outline, memory_context)
    title_and_body = split_title_and_body(draft)
    chapter_id_for_output = next_id or args.chapter_id or "draft_v4"
    chapter_summary = build_summary_from_body(title_and_body["body"])

    chapter_meta_payload = {
        "chapter_id": chapter_id_for_output,
        "kind": "NORMAL",
        "title": title_and_body["title"].replace("##", "").strip(),
        "subtitle": None,
        "volume_id": None,
        "arc_id": None,
        "order_index": int(chapter_id_for_output.replace("chapter_", "")) if chapter_id_for_output.startswith("chapter_") else 0,
        "status": "GENERATED",
        "summary": chapter_summary,
    }

    if next_id:
        input_next_dir = INPUTS_DIR / novel_id / "chapters" / next_id
        write_text(input_next_dir / "chapter.txt", title_and_body["body"])
        write_text(input_next_dir / "title.txt", title_and_body["title"])
        chapter_meta_from_title_compat(
            input_next_dir / "chapter_meta.json",
            chapter_id=next_id,
            title=title_and_body["title"].replace("##", "").strip(),
            summary=chapter_summary,
        )
        write_text(input_next_dir / "output.txt", "generated_by=app.py")
        update_index(INPUTS_DIR / novel_id / "chapters" / "index.txt", next_id, title_and_body["title"], True)

    draft_path = output_dir / "chapter.txt" if (args.chapter_id or next_id) else (output_dir / "draft_v4.txt")
    write_text(draft_path, title_and_body["body"])
    if args.chapter_id or next_id:
        write_text(output_dir / "title.txt", title_and_body["title"])
    chapter_meta_path = output_dir / "chapter_meta.json"
    chapter_meta = write_chapter_meta_contract(
        chapter_meta_path,
        chapter_meta_payload,
        fallback_chapter_id=chapter_id_for_output,
        fallback_title=title_and_body["title"].replace("##", "").strip(),
    )

    tool_runner.save_chapter_draft(draft, next_id or args.chapter_id or "draft_v4")
    tool_runner.flush()

    review_ctx = build_review_context(memory_dir)
    requirement_context = parse_requirement_context(requirements)
    review = generate_review(
        client,
        title_and_body["body"],
        review_ctx["character_summary"],
        review_ctx["world_summary"],
        requirement_context,
        chapter_meta,
    )
    review_path = output_dir / "review.json"
    review = write_review_contract(review_path, review)

    gate = normalize_memory_gate_from_review(
        review=review,
        min_score=args.gate_min_score,
        max_repetition=args.gate_max_repetition,
    )
    gate_path = output_dir / "memory_gate.json"
    write_memory_gate_contract(gate_path, gate)

    if args.update_memory:
        updates_dir = memory_dir / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        base_characters = (
            json.dumps(load_characters_contract(memory_dir / "characters.json"), ensure_ascii=False, indent=2)
            if (memory_dir / "characters.json").exists()
            else ""
        )
        base_world = (memory_dir / "world_rules.md").read_text(encoding="utf-8") if (memory_dir / "world_rules.md").exists() else ""
        base_story = (memory_dir / "story_so_far.md").read_text(encoding="utf-8") if (memory_dir / "story_so_far.md").exists() else ""

        tool_runner.build_characters_delta(title_and_body["body"], base_characters)
        tool_runner.build_world_rules_delta(title_and_body["body"], base_world)
        tool_runner.build_story_so_far_delta(title_and_body["body"], base_story)

        if gate["pass"]:
            merge_characters(memory_dir / "characters.json", updates_dir / "characters_delta.json")
            merge_world_rules(memory_dir / "world_rules.md", updates_dir / "world_rules_delta.md")
            merge_story_so_far(memory_dir / "story_so_far.md", updates_dir / "story_so_far_delta.md")

    print(f"[Saved] {outline_path}")
    print(f"[Saved] {draft_path}")
    print(f"[Saved] {review_path}")


if __name__ == "__main__":
    main()

