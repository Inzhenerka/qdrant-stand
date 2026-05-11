from langchain_qdrant import QdrantVectorStore
from loguru import logger

from stand.config import (
    CorpusConfig,
    EmbedderConfig,
    RAGConfig,
    SplitterConfig,
    StoreConfig,
)
from stand.rag.chunk import load_chunks
from stand.rag.corpus import get_corpus_loader
from stand.rag.embedder import get_embedder
from stand.rag.text_splitter import get_text_splitter
from stand.rag.vector_store import get_vector_store


def ingest_corpus(
    corpus_config: CorpusConfig,
    store_config: StoreConfig,
    splitter_config: SplitterConfig,
    embedder_config: EmbedderConfig,
    force: bool = False,
) -> QdrantVectorStore:
    """Индексирует один корпус в одну коллекцию Qdrant."""
    embedder = get_embedder(embedder_config)
    vector_store, collection_already_exists = get_vector_store(store_config, embedder)
    if collection_already_exists and not force:
        logger.info(f"Reusing existing collection {vector_store.collection_name}")
        return vector_store

    loader = get_corpus_loader(corpus_config)
    splitter = get_text_splitter(splitter_config)
    chunks = load_chunks(loader, splitter)
    logger.info(f"Ingesting corpus: {loader.manifest.name}. Chunks: {len(chunks)}")
    vector_store.add_documents(chunks)
    logger.info(f"Ingested {len(chunks)} chunks into {vector_store.collection_name} collection")
    return vector_store


def ingest_all_corpora(config: RAGConfig, force: bool = False) -> list[str]:
    """Сканирует config.corpora_dir, наливает каждую подпапку в отдельную коллекцию.

    Имя коллекции = имя подпапки. В подпапке обязан лежать manifest.yml.
    """
    if not config.corpora_dir.is_dir():
        raise FileNotFoundError(f"Corpora root not found: {config.corpora_dir}")

    collections: list[str] = []
    for subdir in sorted(config.corpora_dir.iterdir()):
        if not subdir.is_dir():
            continue
        manifest = subdir / "manifest.yml"
        if not manifest.exists():
            logger.warning(f"Skipping {subdir.name}: no manifest.yml")
            continue
        corpus_config = CorpusConfig(text_dir=subdir, manifest_file=manifest)
        store_config = StoreConfig(collection=subdir.name, location=config.store_location)
        ingest_corpus(
            corpus_config=corpus_config,
            store_config=store_config,
            splitter_config=config.splitter,
            embedder_config=config.embedder,
            force=force,
        )
        collections.append(subdir.name)

    if not collections:
        raise RuntimeError(f"No corpora found in {config.corpora_dir} (each must be a subdir with manifest.yml)")
    return collections
