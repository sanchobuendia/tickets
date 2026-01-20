#!/usr/bin/env python
"""
Script de diagnóstico do RAG
"""
from rag_system import get_rag_instance, show_rag_stats

print("\n" + "="*70)
print("🔍 DIAGNÓSTICO DO RAG")
print("="*70 + "\n")

# Verificar estado da base
rag = get_rag_instance()
count = rag.collection.count()

print(f"📊 Documentos na base: {count}")

if count == 0:
    print("\n❌ BASE VAZIA!")
    print("\n💡 Solução:")
    print("   1. Coloque seu CSV na pasta: tickets_historicos.csv")
    print("   2. Execute: python setup_rag.py")
    print("   3. Aguarde mensagem de sucesso")
    print("   4. Execute este script novamente\n")
else:
    print(f"\n✅ Base carregada com {count} documentos!\n")
    show_rag_stats()
    
    # Teste de busca
    print("\n🧪 TESTE DE BUSCA:")
    print("-" * 70)
    results = rag.search_knowledge("computador lento", n_results=3)
    
    if results:
        print(f"✅ Encontrou {len(results)} resultados")
        for i, r in enumerate(results, 1):
            rel = r.get('relevance_score', 0) * 100
            ticket_id = r.get('metadata', {}).get('ticket_id', 'N/A')
            print(f"   {i}. Ticket #{ticket_id} - Relevância: {rel:.1f}%")
    else:
        print("❌ Nenhum resultado encontrado")
    print("-" * 70)

print("\n" + "="*70 + "\n")