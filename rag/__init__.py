"""
Pacote centralizado para componentes e utilitários RAG.
"""
from .knowledge_base import (
    KnowledgeBaseRAG,
    search_knowledge_base,
    load_knowledge_from_csv,
    show_rag_stats,
    get_rag_instance,
)
from .category_code import (
    CategoryCodeRAG,
    get_category_rag_instance,
    search_category_code,
)

__all__ = [
    "KnowledgeBaseRAG",
    "search_knowledge_base",
    "load_knowledge_from_csv",
    "show_rag_stats",
    "get_rag_instance",
    "CategoryCodeRAG",
    "get_category_rag_instance",
    "search_category_code",
]
