# Build stage
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY requirements.txt .
RUN uv venv /app/.venv && uv pip install --no-cache -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PATH=/app/.venv/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8020

ENTRYPOINT ["./entrypoint.sh"]
