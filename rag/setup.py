"""
Script para carregar tickets históricos na base de conhecimento RAG.
"""
import sys
from logger import agent_logger
from rag.knowledge_base import load_knowledge_from_csv, show_rag_stats

log = agent_logger.with_prefix("RAG-SETUP")


def main():
    log.info("Carregador da base de conhecimento")

    csv_path = "exportacao_completa.csv"  # ajuste conforme necessário
    force_reload = len(sys.argv) > 1 and sys.argv[1] == "--force"

    if force_reload:
        log.warning("Modo FORCE RELOAD: limpará a base existente")
    else:
        log.info("Modo INCREMENTAL (mantém base existente)")
        log.info("Use --force para limpar e recarregar tudo")

    try:
        log.info(f"Carregando CSV: {csv_path}")
        load_knowledge_from_csv(csv_path, force_reload=force_reload)
        show_rag_stats()
        log.info("Base de conhecimento pronta para uso")
    except FileNotFoundError:
        log.error(f"Arquivo não encontrado: {csv_path}")
        log.info("Ajuste o caminho do CSV em rag/setup.py")
        sys.exit(1)
    except Exception as exc:
        log.error(f"Erro ao carregar base: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
