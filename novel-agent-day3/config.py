import os
from dotenv import load_dotenv

load_dotenv()

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL = os.getenv("ARK_MODEL", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

if not ARK_API_KEY:
    raise ValueError("Missing ARK_API_KEY. Set it in the environment or .env file.")

if not ARK_MODEL:
    raise ValueError("Missing ARK_MODEL. Set it in the environment or .env file.")
