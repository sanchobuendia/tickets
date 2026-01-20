"""
Script para carregar tickets históricos na base de conhecimento RAG
Execute este script UMA VEZ para popular a base de dados
"""
from rag_system import load_knowledge_from_csv, show_rag_stats
import sys


def main():
    """
    Carrega tickets do CSV para a base de conhecimento
    """
    print("\n" + "="*70)
    print("🚀 CARREGADOR DE BASE DE CONHECIMENTO - SISTEMA RAG")
    print("="*70)
    
    # Caminho do CSV
    csv_path = "exportacao_completa.csv"  # ← AJUSTE ESTE CAMINHO
    
    # Verificar se deve forçar reload
    force_reload = False
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        force_reload = True
        print("⚠️  Modo: FORCE RELOAD (vai limpar base existente)")
    else:
        print("ℹ️  Modo: INCREMENTAL (mantém base existente)")
        print("   Use --force para limpar e recarregar tudo\n")
    
    # Carregar
    try:
        print(f"📂 Carregando tickets de: {csv_path}\n")
        load_knowledge_from_csv(csv_path, force_reload=force_reload)
        
        # Mostrar estatísticas
        print("\n")
        show_rag_stats()
        
        print("✅ Base de conhecimento pronta para uso!")
        print("="*70 + "\n")
        
    except FileNotFoundError:
        print(f"\n❌ ERRO: Arquivo não encontrado: {csv_path}")
        print("\n💡 Ajuste o caminho do CSV no script setup_rag.py")
        print("   Ou coloque o arquivo 'tickets_historicos.csv' na pasta do projeto\n")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERRO ao carregar base: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()