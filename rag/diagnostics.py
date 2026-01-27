"""
Script de diagnóstico do RAG.
"""
from rag.knowledge_base import get_rag_instance, show_rag_stats
from logger import agent_logger

log = agent_logger.with_prefix("RAG-DIAG")


def main():
    log.info("Iniciando diagnóstico do RAG")

    rag = get_rag_instance()
    count = rag.collection.count()
    log.info(f"Documentos na base: {count}")

    if count == 0:
        log.error("Base vazia")
        log.info("1) Coloque seu CSV na pasta: tickets_historicos.csv")
        log.info("2) Execute: python -m rag.setup")
        log.info("3) Execute este script novamente")
        return

    log.info(f"Base carregada com {count} documentos")
    show_rag_stats()

    log.info("Teste de busca: 'computador lento'")
    results = rag.search_knowledge("computador lento", n_results=3)
    if results:
        log.info(f"{len(results)} resultados encontrados")
        for i, r in enumerate(results, 1):
            rel = r.get("relevance_score", 0) * 100
            ticket_id = r.get("metadata", {}).get("ticket_id", "N/A")
            log.info(f"{i}. Ticket #{ticket_id} - Relevância: {rel:.1f}%")
    else:
        log.warning("Nenhum resultado encontrado")


if __name__ == "__main__":
    main()
