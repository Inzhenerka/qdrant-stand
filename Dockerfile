# syntax=docker/dockerfile:1.7

# Stage 1: вытаскиваем бинарь qdrant нужной версии и базовый конфиг
FROM qdrant/qdrant:v1.18.0 AS qdrant-bin

# Stage 2: индексация — поднимаем qdrant в фоне и наливаем коллекцию через REST
FROM python:3.12-slim AS builder

ARG OPENAI_API_KEY
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

COPY --from=qdrant-bin /qdrant/qdrant /usr/local/bin/qdrant
COPY --from=qdrant-bin /qdrant/config /qdrant/config

# qdrant linked against libunwind — нет в python:slim, ставим из bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates libunwind8 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.*

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY stand/ ./stand/
COPY corpus/ ./corpus/
COPY config.yml ingest.py ./

ENV QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage
ENV QDRANT__STORAGE__SNAPSHOTS_PATH=/qdrant/snapshots
RUN mkdir -p /qdrant/storage /qdrant/snapshots

# Поднимаем qdrant фоном -> ждём readyz -> наливаем -> грейсфул-кил -> файлы flushed
RUN set -e && \
    qdrant --config-path /qdrant/config/config.yaml & \
    QDRANT_PID=$! && \
    uv run python ingest.py && \
    kill -TERM "$QDRANT_PID" && \
    wait "$QDRANT_PID" 2>/dev/null || true && \
    ls -la /qdrant/storage/collections/

# Stage 3: финальный образ — обычный qdrant с предзапечённым storage
FROM qdrant/qdrant:v1.18.0

COPY --from=builder /qdrant/storage /qdrant/storage

# Read-only защита:
#   API_KEY  — мастер-ключ для админа (НЕ давать студентам). Сменить на случайный при первом build.
#   READ_ONLY_API_KEY=student — публичный, студенты подключаются с api-key: student.
# Без header — 401. Студентам search/scroll/retrieve работают, upsert/delete возвращают 403.
ENV QDRANT__SERVICE__API_KEY="admin-rotate-me"
ENV QDRANT__SERVICE__READ_ONLY_API_KEY="student"

EXPOSE 6333
# CMD унаследован от qdrant/qdrant
