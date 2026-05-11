"""Точка входа индексации корпусов в локальный Qdrant.

Запускается в builder stage Dockerfile после старта qdrant-server в фоне.
Дожидается /readyz, прогоняет ingest_all_corpora по всем подпапкам corpus/,
выходит — qdrant останавливают извне через SIGTERM, чтобы storage flushed на диск.
"""
import os
import sys
import time
import urllib.error
import urllib.request

from loguru import logger

from stand.config import Config
from stand.rag.ingestion import ingest_all_corpora


def wait_for_qdrant(url: str = "http://127.0.0.1:6333/readyz", timeout: int = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    logger.info("Qdrant ready")
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Qdrant did not become ready in {timeout}s")


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY missing — pass via --build-arg OPENAI_API_KEY=...")
        return 1
    config = Config.from_yaml_file("config.yml")
    wait_for_qdrant()
    collections = ingest_all_corpora(config.rag, force=True)
    logger.info(f"Indexed {len(collections)} collections: {collections}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
