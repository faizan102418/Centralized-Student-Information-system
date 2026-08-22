FROM python:3.11-slim

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml README.md ./
COPY uv.lock* ./
RUN uv sync --no-dev --extra api

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "chatbot.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
