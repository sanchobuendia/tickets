"""
Sistema RAG (Retrieval-Augmented Generation) para base de conhecimento técnica.
Logs padronizados com prefixo para facilitar rastreamento.
"""
import os
from typing import Any, Dict, List

import chromadb
import pandas as pd
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import Config
from logger import agent_logger

log = agent_logger.with_prefix("RAG-KB")


class KnowledgeBaseRAG:
    def __init__(self):
        """Inicializa o sistema RAG com ChromaDB."""
        os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name="tech_support_kb",
            metadata={"description": "Base de conhecimento de tickets históricos"},
        )

        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)

        log.info(f"Inicializado com {self.collection.count()} documentos")

    def load_tickets_from_csv(self, csv_path: str, force_reload: bool = False):
        """Carrega tickets históricos de um CSV para a base de conhecimento."""
        log.info(f"Carregando tickets de {csv_path}")

        if force_reload and self.collection.count() > 0:
            log.warning("Limpando base existente (force_reload=True)")
            self.client.delete_collection("tech_support_kb")
            self.collection = self.client.create_collection(
                name="tech_support_kb",
                metadata={"description": "Base de conhecimento de tickets históricos"},
            )

        if self.collection.count() > 0 and not force_reload:
            log.info(
                f"Base já contém {self.collection.count()} documentos. "
                "Use force_reload=True para recarregar."
            )
            return

        try:
            df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
            log.info(f"CSV carregado com {len(df)} linhas")

            added_count = 0
            skipped_count = 0

            for idx, row in df.iterrows():
                try:
                    name = str(row["name"]) if pd.notna(row["name"]) else ""
                    description = str(row["description"]) if pd.notna(row["description"]) else ""
                    ticket_type = str(row["type"]) if pd.notna(row["type"]) else ""
                    questions = str(row["questions"]) if pd.notna(row["questions"]) else ""
                    steps = str(row["steps"]) if pd.notna(row["steps"]) else ""

                    if not name and not description:
                        skipped_count += 1
                        continue

                    content_parts = []
                    if name:
                        content_parts.append(f"Nome: {name}")
                    if description:
                        desc_clean = description.replace("\n", " ").replace("\r", " ").strip()
                        content_parts.append(f"Descrição: {desc_clean}")
                    if ticket_type:
                        content_parts.append(f"Tipo: {ticket_type}")
                    if questions:
                        questions_clean = questions.replace("\n", " ").replace("\r", " ").strip()
                        content_parts.append(f"Perguntas: {questions_clean}")
                    if steps:
                        steps_clean = steps.replace("\n", " ").replace("\r", " ").strip()
                        content_parts.append(f"Passos: {steps_clean}")

                    content = " | ".join(content_parts)
                    metadata = {
                        "name": name[:200] if name else "",
                        "type": ticket_type,
                        "has_questions": "sim" if questions else "não",
                        "has_steps": "sim" if steps else "não",
                    }

                    self.add_document(
                        doc_id=f"ticket_{idx}",
                        content=content,
                        metadata=metadata,
                    )
                    added_count += 1

                    if added_count % 50 == 0:
                        log.info(f"Processados {added_count} registros...")

                except Exception as exc:
                    log.error(f"Erro na linha {idx}: {exc}")
                    skipped_count += 1

            log.success("Base de conhecimento carregada")
            log.info(f"Registros adicionados: {added_count}")
            log.info(f"Registros pulados: {skipped_count}")
            log.info(f"Total na base: {self.collection.count()}")

        except FileNotFoundError:
            log.error(f"Arquivo não encontrado: {csv_path}")
        except Exception as exc:
            log.error(f"Erro ao carregar CSV: {exc}")

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, str] | None = None):
        """Adiciona um documento à base de conhecimento."""
        self.collection.add(ids=[doc_id], documents=[content], metadatas=[metadata or {}])

    def search_knowledge(
        self, query: str, n_results: int = 3, filter_metadata: Dict[str, str] | None = None
    ) -> List[Dict[str, Any]]:
        """Busca na base de conhecimento."""
        enhanced_query = f"PROBLEMA: {query}"

        results = self.collection.query(
            query_texts=[enhanced_query],
            n_results=n_results,
            where=filter_metadata,
        )

        documents = []
        if results["documents"] and len(results["documents"]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                documents.append(
                    {
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "relevance_score": 1
                        - (results["distances"][0][i] if results["distances"] else 0),
                    }
                )

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da base de conhecimento."""
        total = self.collection.count()

        if total > 0:
            all_data = self.collection.get()
            metadatas = all_data["metadatas"]

            types: Dict[str, int] = {}
            with_questions = 0
            with_steps = 0

            for meta in metadatas:
                ticket_type = meta.get("type", "Desconhecido")
                types[ticket_type] = types.get(ticket_type, 0) + 1
                with_questions += 1 if meta.get("has_questions") == "sim" else 0
                with_steps += 1 if meta.get("has_steps") == "sim" else 0

            return {
                "total_documents": total,
                "with_questions": with_questions,
                "with_steps": with_steps,
                "types": types,
            }

        return {"total_documents": 0}


_rag_instance = None


def get_rag_instance() -> KnowledgeBaseRAG:
    """Retorna instância singleton do RAG."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = KnowledgeBaseRAG()
    return _rag_instance


def search_knowledge_base(query: str, num_results: int = 5) -> str:
    """Busca informações na base de conhecimento técnica."""
    log.info(f"Iniciando busca por '{query}' | top={num_results}")

    rag = get_rag_instance()
    results = rag.search_knowledge(query, n_results=num_results)

    if not results:
        log.warning("Nenhum resultado encontrado")
        log.info("Tamanho do conteúdo retornado: 0 caracteres")
        return "Não encontrei soluções similares na base de conhecimento para este problema específico."

    log.info(f"Encontrados {len(results)} resultados relevantes")

    formatted_results = "📚 **Casos Similares Encontrados na Base de Conhecimento:**\n\n"
    total_chars = 0

    for i, result in enumerate(results, 1):
        content = result["content"]
        metadata = result.get("metadata", {})
        relevance = result.get("relevance_score", 0) * 100

        result_text = f"**Caso {i}** (Relevância: {relevance:.0f}%)\n"
        total_chars += len(result_text)
        formatted_results += result_text

        if metadata.get("name"):
            line = f"📋 **Nome:** {metadata['name']}\n"
            formatted_results += line
            total_chars += len(line)

        if metadata.get("type"):
            line = f"🏷️ **Tipo:** {metadata['type']}\n"
            formatted_results += line
            total_chars += len(line)

        if "Descrição:" in content:
            description = content.split("Descrição:")[1].split("|")[0].strip()
            if description:
                line = f"📝 **Descrição:** {description[:300]}{'...' if len(description) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)

        if "Perguntas:" in content:
            questions = content.split("Perguntas:")[1].split("|")[0].strip()
            if questions:
                line = f"❓ **Perguntas:** {questions[:300]}{'...' if len(questions) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)

        if "Passos:" in content:
            steps = (
                content.split("Passos:")[1].split("|")[0].strip()
                if "|" in content.split("Passos:")[1]
                else content.split("Passos:")[1].strip()
            )
            if steps:
                line = f"📋 **Passos:** {steps[:300]}{'...' if len(steps) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)

        formatted_results += "\n"
        total_chars += 1
        log.info(f"Resultado {i}: {metadata.get('name', 'N/A')[:50]} | relevância {relevance:.0f}%")

    formatted_results += "💡 **Sugestão:** Use essas soluções como base para resolver o problema atual.\n"
    total_chars += len("💡 **Sugestão:** Use essas soluções como base para resolver o problema atual.\n")

    avg_relevance = sum(r.get("relevance_score", 0) for r in results) / len(results) * 100
    log.info(
        f"Resumo: resultados={len(results)}, tamanho={total_chars:,} chars, "
        f"média={total_chars // len(results):,} chars, relevância média={avg_relevance:.1f}%"
    )

    return formatted_results


def load_knowledge_from_csv(csv_path: str, force_reload: bool = False):
    """Função helper para carregar base de conhecimento de CSV."""
    rag = get_rag_instance()
    rag.load_tickets_from_csv(csv_path, force_reload=force_reload)


def show_rag_stats():
    """Mostra estatísticas da base de conhecimento."""
    rag = get_rag_instance()
    stats = rag.get_stats()

    print("\n" + "=" * 60)
    print("📊 ESTATÍSTICAS DA BASE DE CONHECIMENTO")
    print("=" * 60)
    print(f"📚 Total de documentos: {stats.get('total_documents', 0)}")
    print(f"❓ Com perguntas: {stats.get('with_questions', 0)}")
    print(f"📝 Com passos: {stats.get('with_steps', 0)}")

    if "types" in stats and stats["types"]:
        print("\n📁 Distribuição por tipo:")
        for ticket_type, count in sorted(stats["types"].items(), key=lambda x: x[1], reverse=True):
            print(f"   • {ticket_type}: {count} registros")

    print("=" * 60 + "\n")
