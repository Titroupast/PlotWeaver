from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

PLANNER_SYSTEM_PROMPT = (PROMPTS_DIR / "planner.txt").read_text(encoding="utf-8")
WRITER_SYSTEM_PROMPT = (PROMPTS_DIR / "writer.txt").read_text(encoding="utf-8")
REVIEWER_SYSTEM_PROMPT = (PROMPTS_DIR / "reviewer.txt").read_text(encoding="utf-8")

PLANNER_USER_TEMPLATE = (PROMPTS_DIR / "planner_user.txt").read_text(encoding="utf-8")
WRITER_USER_TEMPLATE = (PROMPTS_DIR / "writer_user.txt").read_text(encoding="utf-8")
REVIEWER_USER_TEMPLATE = (PROMPTS_DIR / "reviewer_user.txt").read_text(encoding="utf-8")
