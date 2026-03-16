FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/src /app/src
COPY packages /app/packages

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "plotweaver_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
