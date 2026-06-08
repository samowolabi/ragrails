FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY ragrails ./ragrails

RUN uv pip install --no-cache-dir ".[server-qdrant,url]" \
  && python -m playwright install --with-deps chromium

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=3).read()"

CMD ["ragrails-api", "--host", "0.0.0.0", "--port", "8000"]
