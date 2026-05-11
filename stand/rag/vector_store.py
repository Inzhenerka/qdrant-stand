from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from stand.config import StoreConfig


def get_vector_store(
    config: StoreConfig,
    embedder: OpenAIEmbeddings,
) -> tuple[QdrantVectorStore, bool]:
    """Подключаемся к хранилищу Qdrant, создаем коллекцию, привязываем embedder."""

    location = config.location
    if location == ":memory:":
        client = QdrantClient(location=location)
    elif location.startswith(("http://", "https://")):
        client = QdrantClient(url=location)
    else:
        client = QdrantClient(path=location)

    collection_already_exists = client.collection_exists(config.collection)

    if not collection_already_exists:
        client.create_collection(
            collection_name=config.collection,
            vectors_config=VectorParams(size=embedder.dimensions, distance=Distance.COSINE),
        )

    store = QdrantVectorStore(
        client=client,
        collection_name=config.collection,
        embedding=embedder,
    )
    return store, collection_already_exists
