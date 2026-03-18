from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


@lru_cache(maxsize=64)
def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


def render_prompt(template_name: str, **kwargs: object) -> str:
    template = load_prompt(template_name)
    # Only replace explicit {key} placeholders; keep all other braces (e.g. JSON examples) untouched.
    rendered = template
    values = _SafeDict({k: "" if v is None else str(v) for k, v in kwargs.items()})
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered
