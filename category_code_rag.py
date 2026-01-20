"""
Sistema RAG para classificação de código de categoria
Busca na collection "codigo" para encontrar o código mais adequado
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from config import Config
import os
from logger import agent_logger


class CategoryCodeRAG:
    """RAG especializado em buscar códigos de categoria"""
    
    def __init__(self):
        """Inicializa o sistema RAG para códigos"""
        # Criar diretório se não existir
        os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        
        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Obter collection "codigo"
        try:
            self.collection = self.client.get_collection(name="codigo")
            agent_logger.info(f"📚 RAG de Códigos inicializado com {self.collection.count()} códigos")
        except Exception as e:
            agent_logger.error(f"❌ Erro ao carregar collection 'codigo': {e}")
            raise
        
        # Modelo de embeddings (mesmo modelo usado na criação)
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
    
    def search_category_code(
        self, 
        problem_description: str, 
        n_results: int = 5,
        filter_grupo: str = None
    ) -> List[Dict[str, Any]]:
        """
        Busca códigos de categoria relevantes baseado na descrição do problema
        
        Args:
            problem_description: Descrição do problema/chamado
            n_results: Número de resultados a retornar
            filter_grupo: Filtrar por grupo específico (opcional)
        
        Returns:
            Lista de códigos encontrados com metadados
        """
        # Preparar filtro se especificado
        where_filter = None
        if filter_grupo:
            where_filter = {"grupo_solucao": filter_grupo}
        
        # Realizar busca semântica
        results = self.collection.query(
            query_texts=[problem_description],
            n_results=n_results,
            where=where_filter
        )
        
        documents = []
        if results and results['documents']:
            for i in range(len(results['documents'][0])):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else None
                
                documents.append({
                    "content": results['documents'][0][i],
                    "metadata": metadata,
                    "distance": distance,
                    "relevance_score": 1 - distance if distance else 0,
                    # Campos importantes para o agente
                    "codigo_categoria": metadata.get('codigo_categoria', ''),
                    "grupo_solucao": metadata.get('grupo_solucao', ''),
                    "descricao": metadata.get('descricao', ''),
                    "descricao_completa": metadata.get('descricao_completa', '')
                })
        
        return documents


# Instância global
_category_rag_instance = None


def get_category_rag_instance() -> CategoryCodeRAG:
    """Retorna instância singleton do RAG de códigos"""
    global _category_rag_instance
    if _category_rag_instance is None:
        _category_rag_instance = CategoryCodeRAG()
    return _category_rag_instance


def search_category_code(problem_description: str, num_results: int = 5, filter_grupo: str = None) -> str:
    """
    Busca códigos de categoria relevantes na base de conhecimento.
    Use esta função para encontrar o código de categoria mais adequado para um chamado.
    
    Args:
        problem_description: Descrição do problema/chamado do usuário
        num_results: Número de resultados a retornar (padrão: 5)
        filter_grupo: Filtrar por grupo específico, ex: "Help Desk" (opcional)
    
    Returns:
        String formatada com os códigos encontrados e suas descrições
    
    Examples:
        >>> search_category_code("usuário não consegue acessar o email")
        >>> search_category_code("problema com impressora", filter_grupo="Help Desk")
    """
    # Log início da busca
    agent_logger.info("\n" + "="*70)
    agent_logger.info("🔍 RAG DE CÓDIGOS INICIADO")
    agent_logger.info("="*70)
    agent_logger.info(f"📝 Descrição do problema: '{problem_description}'")
    agent_logger.info(f"🎯 Top: {num_results} resultados")
    if filter_grupo:
        agent_logger.info(f"📁 Filtro de grupo: {filter_grupo}")
    
    rag = get_category_rag_instance()
    results = rag.search_category_code(
        problem_description=problem_description,
        n_results=num_results,
        filter_grupo=filter_grupo
    )
    
    if not results:
        agent_logger.warning("⚠️  RAG: Nenhum código encontrado")
        agent_logger.info("="*70 + "\n")
        return "Não foram encontrados códigos de categoria para este tipo de problema."
    
    # Log de sucesso
    agent_logger.info(f"✅ RAG: Encontrados {len(results)} códigos relevantes")
    
    # Formatar resultados
    formatted_results = "📋 **Códigos de Categoria Encontrados:**\n\n"
    
    for i, result in enumerate(results, 1):
        relevance = result.get('relevance_score', 0) * 100
        codigo_categoria = result.get('codigo_categoria', 'N/A')
        grupo = result.get('grupo_solucao', 'N/A')
        descricao = result.get('descricao', 'N/A')
        descricao_completa = result.get('descricao_completa', '')
        
        formatted_results += f"**Opção {i}** (Relevância: {relevance:.0f}%)\n"
        formatted_results += f"🔢 **Código da Categoria:** {codigo_categoria}\n"
        formatted_results += f"📁 **Grupo:** {grupo}\n"
        formatted_results += f"📝 **Descrição:** {descricao}\n"
        
        if descricao_completa and descricao_completa != descricao:
            # Limitar tamanho da descrição completa
            desc_truncated = descricao_completa[:200] + ('...' if len(descricao_completa) > 200 else '')
            formatted_results += f"📄 **Detalhes:** {desc_truncated}\n"
        
        formatted_results += "\n"
        
        # Log individual
        agent_logger.info(f"   • Código {codigo_categoria} ({grupo}) - Relevância: {relevance:.0f}%")
    
    formatted_results += "💡 **Instruções:** Escolha o código mais adequado baseado na descrição do problema do usuário.\n"
    
    # Log final
    agent_logger.info(f"\n📊 ESTATÍSTICAS:")
    agent_logger.info(f"   • Códigos retornados: {len(results)}")
    avg_relevance = sum(r.get('relevance_score', 0) for r in results) / len(results) * 100
    agent_logger.info(f"   • Relevância média: {avg_relevance:.1f}%")
    agent_logger.info("="*70 + "\n")
    
    return formatted_results