from __future__ import annotations

import importlib.util

from plotweaver_api.db.settings import settings


def main() -> None:
    has_openai = importlib.util.find_spec("openai") is not None
    print("openai_installed:", has_openai)
    print("ark_api_key_set:", bool(settings.ark_api_key))
    print("ark_model:", settings.ark_model or "<empty>")
    print("ark_base_url:", settings.ark_base_url)

    if not has_openai:
        print("hint: 在当前解释器执行 `uv pip install -e .` 或 `uv pip install openai`")
    if not settings.ark_api_key or not settings.ark_model:
        print("hint: 在 apps/api/.env 设置 ARK_API_KEY 与 ARK_MODEL 后重启 API")


if __name__ == "__main__":
    main()