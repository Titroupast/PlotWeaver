import os
from dotenv import load_dotenv

load_dotenv()

ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL = os.getenv("ARK_MODEL", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

if not ARK_API_KEY:
    raise ValueError("缺少 ARK_API_KEY，请先配置环境变量或 .env 文件。")

if not ARK_MODEL:
    raise ValueError("缺少 ARK_MODEL，请先填写你在火山方舟控制台可用的模型 ID。")