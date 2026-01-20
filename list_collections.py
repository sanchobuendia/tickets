import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

collections = client.list_collections()

for col in collections:
    print(f"{col.name}: {col.count()} documentos")