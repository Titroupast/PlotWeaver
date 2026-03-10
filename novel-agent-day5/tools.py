from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


def _safe_slug(text: str) -> str:
    return "".join(ch for ch in text.strip() if ch.isalnum() or ch in ("_", "-"))[:32] or "unknown"


class ToolRunner:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        memory_dir: Path,
        run_log_path: Path,
        prompts_dir: Path,
        output_dir: Path,
    ):
        self.client = client
        self.model = model
        self.memory_dir = memory_dir
        self.run_log_path = run_log_path
        self.prompts_dir = prompts_dir
        self.output_dir = output_dir
        self.logs: List[Dict[str, Any]] = []

    def _write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _log(self, name: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        self.logs.append({"tool": name, "inputs": inputs, "outputs": outputs})

    def _call(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()

    def _read_prompt(self, filename: str) -> str:
        return (self.prompts_dir / filename).read_text(encoding="utf-8")

    def build_characters(self, chapters_text: str) -> Path:
        system_prompt = self._read_prompt("memory_characters.txt")
        user_prompt = chapters_text
        content = self._call(system_prompt, user_prompt, temperature=0.2)
        out_path = self.memory_dir / "characters.json"
        self._write(out_path, content)
        self._log("build_characters", {"chapters_len": len(chapters_text)}, {"path": str(out_path)})
        return out_path

    def build_world_rules(self, chapters_text: str) -> Path:
        system_prompt = self._read_prompt("memory_world_rules.txt")
        user_prompt = chapters_text
        content = self._call(system_prompt, user_prompt, temperature=0.2)
        out_path = self.memory_dir / "world_rules.md"
        self._write(out_path, content)
        self._log("build_world_rules", {"chapters_len": len(chapters_text)}, {"path": str(out_path)})
        return out_path

    def build_story_so_far(self, chapters_text: str) -> Path:
        system_prompt = self._read_prompt("memory_story_so_far.txt")
        user_prompt = chapters_text
        content = self._call(system_prompt, user_prompt, temperature=0.2)
        out_path = self.memory_dir / "story_so_far.md"
        self._write(out_path, content)
        self._log("build_story_so_far", {"chapters_len": len(chapters_text)}, {"path": str(out_path)})
        return out_path

    def save_chapter_draft(self, text: str, chapter_id: str) -> Path:
        out_path = self.output_dir / f"draft_{_safe_slug(chapter_id)}.txt"
        self._write(out_path, text)
        self._log("save_chapter_draft", {"chapter_id": chapter_id}, {"path": str(out_path)})
        return out_path

    def flush(self) -> None:
        self._write(self.run_log_path, json.dumps(self.logs, ensure_ascii=False, indent=2))
