# backend/Dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Basic Python env hygiene
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# System dependencies (curl for healthcheck, gcc for any compiled deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ---- Install Python dependencies ----
# Build context is ./backend, so this is backend/requirements.txt in the repo
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pytest pytest-asyncio httpx aiohttp

# ---- Copy application code ----
# This copies everything under ./backend into /app
COPY . .

# Optional: ensure expected dirs exist
RUN mkdir -p app/routers tests

# ---- Runtime config ----
EXPOSE 8001

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8001/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
