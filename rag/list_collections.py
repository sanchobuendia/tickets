"""
Lista coleções disponíveis no ChromaDB com contagem de documentos.
"""
import chromadb
from chromadb.config import Settings
from logger import agent_logger

log = agent_logger.with_prefix("RAG-LIST")


def main():
    client = chromadb.PersistentClient(
        path="./chroma_db",
        settings=Settings(anonymized_telemetry=False),
    )

    collections = client.list_collections()
    if not collections:
        log.info("Nenhuma collection encontrada em ./chroma_db")
        return

    for col in collections:
        log.info(f"{col.name}: {col.count()} documentos")


if __name__ == "__main__":
    main()
