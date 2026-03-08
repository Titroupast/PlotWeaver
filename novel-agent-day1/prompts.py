from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

SYSTEM_PROMPT = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
USER_TEMPLATE = (PROMPTS_DIR / "user.txt").read_text(encoding="utf-8")
