# syntax=docker/dockerfile:1

# ---------- build ----------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv==0.12.5

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src

# Everything lands in one relocatable virtualenv that the runtime stage copies whole,
# so no build tooling reaches the final image.
RUN uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache .

# ---------- runtime ----------
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
USER appuser

EXPOSE 8000

# Liveness only. curl without -f treats 503 as a reply, which is what /health returns
# while CelesTrak is unreachable: the app is up, it just has nothing to serve yet.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -sS -o /dev/null http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "iss_tracker.main:app", "--host", "0.0.0.0", "--port", "8000"]
