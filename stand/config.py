from typing import Self
from pathlib import Path

import yaml
from pydantic import BaseModel


class CorpusConfig(BaseModel):
    text_dir: Path
    manifest_file: Path


class SplitterConfig(BaseModel):
    chunk_size: int = 900
    chunk_overlap: int = 180


class EmbedderConfig(BaseModel):
    model: str = "text-embedding-3-small"
    base_url: str | None = None
    dimensions: int = 1536
    timeout: float = 30.0


class StoreConfig(BaseModel):
    collection: str
    location: str = ":memory:"


class RAGConfig(BaseModel):
    corpora_dir: Path = Path("corpus")
    splitter: SplitterConfig
    embedder: EmbedderConfig
    store_location: str = ":memory:"


class Config(BaseModel):
    rag: RAGConfig

    @classmethod
    def from_yaml_file(cls, config_path: str | Path = "config.yml") -> Self:
        config_str = Path(config_path).read_text(encoding="utf-8")
        config_dict = yaml.safe_load(config_str)
        return cls.model_validate(config_dict)
