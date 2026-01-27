"""
Script utilitário para criar/atualizar a collection "codigo" no ChromaDB.
Logs padronizados via agent_logger.
"""
import os
from typing import Dict

import chromadb
import pandas as pd
from chromadb.config import Settings
from logger import agent_logger
from sentence_transformers import SentenceTransformer

log = agent_logger.with_prefix("RAG-COLLECTION")


class SingleCollectionManager:
    """Gerencia uma única collection no ChromaDB."""

    def __init__(
        self,
        chroma_persist_directory: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        os.makedirs(chroma_persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=chroma_persist_directory, settings=Settings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer(embedding_model)

        log.info(f"ChromaDB inicializado em {chroma_persist_directory}")

    def load_data_from_csv(
        self, csv_path: str, collection_name: str = "codigo", force_reload: bool = False
    ):
        """Carrega dados do CSV em uma única collection."""
        log.info(f"CSV: {csv_path} | collection: {collection_name} | force_reload={force_reload}")

        try:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8-sig")
            log.info(f"{len(df)} registros encontrados no CSV")

            if force_reload:
                try:
                    log.warning(f"Removendo collection existente '{collection_name}'")
                    self.client.delete_collection(collection_name)
                except Exception:
                    log.warning(f"Collection '{collection_name}' não existia; prosseguindo")

            collection = self.client.get_or_create_collection(
                name=collection_name, metadata={"description": "Base de conhecimento de códigos"}
            )

            if collection.count() > 0 and not force_reload:
                log.info(f"Collection já contém {collection.count()} documentos; use force_reload=True para recarregar.")
                return

            added_count = 0
            skipped_count = 0

            for idx, row in df.iterrows():
                try:
                    grupo_solucao = str(row.get("Descrição do grupo de solução", "") or "")
                    desc_completa = str(row.get("Descrição completa", "") or "")
                    descricao = str(row.get("Descrição", "") or "")
                    codigo_grupo = str(row.get("Código do grupo de solução", "") or "")
                    codigo_categoria = str(row.get("Código da categoria", "") or "")

                    if not desc_completa and not descricao and not grupo_solucao:
                        skipped_count += 1
                        continue

                    content_parts = []
                    if grupo_solucao:
                        content_parts.append(f"Grupo: {grupo_solucao}")
                    if desc_completa:
                        content_parts.append(f"Descrição Completa: {desc_completa}")
                    if descricao:
                        content_parts.append(f"Descrição: {descricao}")
                    if codigo_grupo:
                        content_parts.append(f"Código do Grupo: {codigo_grupo}")
                    if codigo_categoria:
                        content_parts.append(f"Código da Categoria: {codigo_categoria}")

                    content = " | ".join(content_parts)
                    metadata: Dict[str, str] = {
                        "grupo_solucao": grupo_solucao,
                        "descricao_completa": desc_completa[:500] if desc_completa else "",
                        "descricao": descricao[:200] if descricao else "",
                        "codigo_grupo": codigo_grupo,
                        "codigo_categoria": codigo_categoria,
                    }

                    doc_id = f"doc_{codigo_categoria}_{idx}"
                    collection.add(ids=[doc_id], documents=[content], metadatas=[metadata])

                    added_count += 1
                    if added_count % 100 == 0:
                        log.info(f"Processados {added_count} documentos...")

                except Exception as exc:
                    log.warning(f"Erro na linha {idx}: {exc}")
                    skipped_count += 1

            log.info(f"Documentos adicionados: {added_count} | pulados: {skipped_count} | total: {collection.count()}")

        except FileNotFoundError:
            log.error(f"Arquivo não encontrado: {csv_path}")
        except Exception as exc:
            log.error(f"Erro ao carregar CSV: {exc}")

    def get_collection_stats(self, collection_name: str = "codigo"):
        """Retorna estatísticas da collection."""
        try:
            collection = self.client.get_collection(collection_name)
            total = collection.count()

            if total > 0:
                metadatas = collection.get()["metadatas"]
                grupos: Dict[str, int] = {}
                for meta in metadatas:
                    grupo = meta.get("grupo_solucao", "Desconhecido")
                    grupos[grupo] = grupos.get(grupo, 0) + 1

                return {"collection_name": collection_name, "total_documentos": total, "grupos": grupos}

            return {"collection_name": collection_name, "total_documentos": 0}

        except Exception as exc:
            return {"erro": str(exc)}

    def search(
        self, query: str, collection_name: str = "codigo", n_results: int = 5, filter_grupo: str | None = None
    ):
        """Busca na collection."""
        try:
            collection = self.client.get_collection(collection_name)
            where_filter = {"grupo_solucao": filter_grupo} if filter_grupo else None

            results = collection.query(query_texts=[query], n_results=n_results, where=where_filter)

            documents = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    documents.append(
                        {
                            "content": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "distance": results["distances"][0][i] if results["distances"] else None,
                        }
                    )

            return documents

        except Exception as exc:
            log.error(f"Erro ao buscar: {exc}")
            return []


def main():
    """Função principal para execução CLI."""
    CSV_PATH = "codigos.csv"
    CHROMA_DIR = "./chroma_db"
    COLLECTION_NAME = "codigo"
    FORCE_RELOAD = False

    log.info("Iniciando criação/atualização da collection 'codigo'")

    manager = SingleCollectionManager(
        chroma_persist_directory=CHROMA_DIR,
        embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )

    manager.load_data_from_csv(CSV_PATH, collection_name=COLLECTION_NAME, force_reload=FORCE_RELOAD)

    stats = manager.get_collection_stats(COLLECTION_NAME)
    if "erro" in stats:
        log.error(f"Erro: {stats['erro']}")
    else:
        log.info(f"Collection {stats['collection_name']} com {stats['total_documentos']} documentos")
        if stats.get("grupos"):
            top_grupos = sorted(stats["grupos"].items(), key=lambda x: x[1], reverse=True)[:5]
            for grupo, count in top_grupos:
                log.info(f"Grupo {grupo}: {count} docs")

    log.info("Processo concluído")


if __name__ == "__main__":
    main()
