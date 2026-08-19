FROM python:3.14.7-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv

COPY requirements-build.lock requirements-prod.lock ./

RUN /opt/venv/bin/python -m pip install --require-hashes --no-deps -r requirements-build.lock \
    && /opt/venv/bin/python -m pip install --require-hashes -r requirements-prod.lock

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN /opt/venv/bin/python -m pip install --no-deps --no-build-isolation .


FROM python:3.14.7-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANNIE_DATA_DIR=/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system annie \
    && useradd --system --gid annie --create-home --home-dir /home/annie annie

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=annie:annie migrations ./migrations
COPY --chown=annie:annie scripts ./scripts

RUN mkdir -p /data \
    && chown annie:annie /data

USER annie

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8787/api/live || exit 1

STOPSIGNAL SIGTERM

CMD ["uvicorn", "annie.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8787"]
