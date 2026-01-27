"""
Sistema RAG para classificação de código de categoria.
Logs padronizados com prefixo para facilitar rastreamento.
"""
from typing import Any, Dict, List

import chromadb
import os
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import Config
from logger import agent_logger

log = agent_logger.with_prefix("RAG-CODE")


class CategoryCodeRAG:
    """RAG especializado em buscar códigos de categoria."""

    def __init__(self):
        os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False),
        )

        try:
            self.collection = self.client.get_collection(name="codigo")
            log.info(f"Inicializado com {self.collection.count()} códigos")
        except Exception as exc:
            log.error(f"Erro ao carregar collection 'codigo': {exc}")
            raise

        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)

    def search_category_code(
        self, problem_description: str, n_results: int = 5, filter_grupo: str | None = None
    ) -> List[Dict[str, Any]]:
        """Busca códigos de categoria relevantes baseado na descrição do problema."""
        where_filter = {"grupo_solucao": filter_grupo} if filter_grupo else None

        results = self.collection.query(
            query_texts=[problem_description],
            n_results=n_results,
            where=where_filter,
        )

        documents = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else None

                documents.append(
                    {
                        "content": results["documents"][0][i],
                        "metadata": metadata,
                        "distance": distance,
                        "relevance_score": 1 - distance if distance else 0,
                        "codigo_categoria": metadata.get("codigo_categoria", ""),
                        "grupo_solucao": metadata.get("grupo_solucao", ""),
                        "descricao": metadata.get("descricao", ""),
                        "descricao_completa": metadata.get("descricao_completa", ""),
                    }
                )

        return documents


_category_rag_instance = None


def get_category_rag_instance() -> CategoryCodeRAG:
    """Retorna instância singleton do RAG de códigos."""
    global _category_rag_instance
    if _category_rag_instance is None:
        _category_rag_instance = CategoryCodeRAG()
    return _category_rag_instance


def search_category_code(problem_description: str, num_results: int = 5, filter_grupo: str | None = None) -> str:
    """
    Busca códigos de categoria relevantes na base de conhecimento.
    Retorna string formatada com os códigos encontrados e suas descrições.
    """
    log.info(f"Buscando código de categoria | top={num_results} | descrição='{problem_description}'")
    if filter_grupo:
        log.info(f"Filtro de grupo: {filter_grupo}")

    rag = get_category_rag_instance()
    results = rag.search_category_code(
        problem_description=problem_description,
        n_results=num_results,
        filter_grupo=filter_grupo,
    )

    if not results:
        log.warning("Nenhum código retornado; sugerindo código genérico")
        return "CÓDIGO SUGERIDO: 0000\nGRUPO: Help Desk\nDESCRIÇÃO: Código genérico aplicado por falta de correspondência\nJUSTIFICATIVA: Base sem correspondências; usar código genérico"

    log.info(f"{len(results)} códigos relevantes encontrados")

    formatted_results = "📋 **Códigos de Categoria Encontrados:**\n\n"

    for i, result in enumerate(results, 1):
        relevance = result.get("relevance_score", 0) * 100
        codigo_categoria = result.get("codigo_categoria", "N/A")
        grupo = result.get("grupo_solucao", "N/A")
        descricao = result.get("descricao", "N/A")
        descricao_completa = result.get("descricao_completa", "")

        formatted_results += f"**Opção {i}** (Relevância: {relevance:.0f}%)\n"
        formatted_results += f"🔢 **Código da Categoria:** {codigo_categoria}\n"
        formatted_results += f"📁 **Grupo:** {grupo}\n"
        formatted_results += f"📝 **Descrição:** {descricao}\n"

        if descricao_completa and descricao_completa != descricao:
            desc_truncated = descricao_completa[:200] + ("..." if len(descricao_completa) > 200 else "")
            formatted_results += f"📄 **Detalhes:** {desc_truncated}\n"

        formatted_results += "\n"
        log.info(f"Código {codigo_categoria} ({grupo}) | relevância {relevance:.0f}%")

    formatted_results += (
        "💡 **Instruções:** Escolha o código mais adequado baseado na descrição do problema do usuário.\n"
    )

    avg_relevance = sum(r.get("relevance_score", 0) for r in results) / len(results) * 100
    log.info(f"Resumo: retornados={len(results)} | relevância média={avg_relevance:.1f}%")

    return formatted_results
