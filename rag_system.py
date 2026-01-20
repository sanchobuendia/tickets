"""
Sistema RAG (Retrieval-Augmented Generation) para base de conhecimento técnica
OTIMIZADO: Carrega tickets históricos de CSV para aprendizado
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from config import Config
import os
import pandas as pd
from datetime import datetime
from logger import agent_logger


class KnowledgeBaseRAG:
    def __init__(self):
        """Inicializa o sistema RAG com ChromaDB"""
        # Criar diretório se não existir
        os.makedirs(Config.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        
        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(
            path=Config.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Criar ou obter coleção
        self.collection = self.client.get_or_create_collection(
            name="tech_support_kb",
            metadata={"description": "Base de conhecimento de tickets históricos"}
        )
        
        # Modelo de embeddings
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        
        agent_logger.info(f"📚 RAG inicializado com {self.collection.count()} documentos")
    
    def load_tickets_from_csv(self, csv_path: str, force_reload: bool = False):
        """
        Carrega tickets históricos de um CSV para a base de conhecimento
        
        Args:
            csv_path: Caminho para o arquivo CSV
            force_reload: Se True, limpa a base e recarrega tudo
        """
        agent_logger.info(f"📂 Carregando tickets de: {csv_path}")
        
        # Se force_reload, limpar base
        if force_reload and self.collection.count() > 0:
            agent_logger.warning("🗑️  Limpando base de conhecimento existente...")
            self.client.delete_collection("tech_support_kb")
            self.collection = self.client.create_collection(
                name="tech_support_kb",
                metadata={"description": "Base de conhecimento de tickets históricos"}
            )
        
        # Verificar se já tem documentos e não é reload
        if self.collection.count() > 0 and not force_reload:
            agent_logger.info(f"✅ Base já contém {self.collection.count()} documentos. Use force_reload=True para recarregar.")
            return
        
        try:
            # Ler CSV com separador correto (ponto e vírgula)
            # e encoding que suporta BOM
            df = pd.read_csv(
                csv_path, 
                sep=';',           # ← Separador correto
                encoding='utf-8-sig'  # ← Remove BOM automaticamente
            )
            agent_logger.info(f"📊 CSV carregado: {len(df)} registros encontrados")
            
            # Processar cada registro
            added_count = 0
            skipped_count = 0
            
            for idx, row in df.iterrows():
                try:
                    # Extrair informações de cada coluna
                    name = str(row['name']) if pd.notna(row['name']) else ""
                    description = str(row['description']) if pd.notna(row['description']) else ""
                    ticket_type = str(row['type']) if pd.notna(row['type']) else ""
                    questions = str(row['questions']) if pd.notna(row['questions']) else ""
                    steps = str(row['steps']) if pd.notna(row['steps']) else ""
                    
                    # Pular se não tem informação útil
                    if not name and not description:
                        skipped_count += 1
                        continue
                    
                    # CONTENT: Concatenar TODAS as colunas
                    # Formato: texto corrido com todas as informações
                    content_parts = []
                    
                    if name:
                        content_parts.append(f"Nome: {name}")
                    if description:
                        # Limpar quebras de linha
                        desc_clean = description.replace('\n', ' ').replace('\r', ' ').strip()
                        content_parts.append(f"Descrição: {desc_clean}")
                    if ticket_type:
                        content_parts.append(f"Tipo: {ticket_type}")
                    if questions:
                        # Limpar quebras de linha
                        questions_clean = questions.replace('\n', ' ').replace('\r', ' ').strip()
                        content_parts.append(f"Perguntas: {questions_clean}")
                    if steps:
                        # Limpar quebras de linha
                        steps_clean = steps.replace('\n', ' ').replace('\r', ' ').strip()
                        content_parts.append(f"Passos: {steps_clean}")
                    
                    # Juntar tudo com " | " como separador
                    content = " | ".join(content_parts)
                    
                    # METADADOS: Um campo para cada coluna
                    metadata = {
                        "name": name[:200] if name else "",  # Limitar tamanho
                        "type": ticket_type,
                        "has_questions": "sim" if questions else "não",
                        "has_steps": "sim" if steps else "não"
                    }
                    
                    # Adicionar à base
                    self.add_document(
                        doc_id=f"ticket_{idx}",  # Usar idx para garantir unicidade
                        content=content,
                        metadata=metadata
                    )
                    
                    added_count += 1
                    
                    # Log a cada 50 registros
                    if added_count % 50 == 0:
                        agent_logger.info(f"   📝 Processados: {added_count} registros...")
                
                except Exception as e:
                    agent_logger.error(f"   ❌ Erro ao processar registro linha {idx}: {e}")
                    skipped_count += 1
                    continue
            
            agent_logger.success(f"✅ Base de conhecimento carregada!")
            agent_logger.info(f"   📊 Registros adicionados: {added_count}")
            agent_logger.info(f"   ⏭️  Registros pulados: {skipped_count}")
            agent_logger.info(f"   📚 Total na base: {self.collection.count()}")
            
        except FileNotFoundError:
            agent_logger.error(f"❌ Arquivo não encontrado: {csv_path}")
        except Exception as e:
            agent_logger.error(f"❌ Erro ao carregar CSV: {e}")
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, str] = None):
        """Adiciona um documento à base de conhecimento"""
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata or {}]
        )
    
    def search_knowledge(
        self, 
        query: str, 
        n_results: int = 3,
        filter_metadata: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca na base de conhecimento
        
        Args:
            query: Consulta do usuário
            n_results: Número de resultados a retornar
            filter_metadata: Filtros opcionais (ex: {"solution_group": "Help Desk"})
        
        Returns:
            Lista de documentos relevantes
        """
        # Melhorar query para busca semântica
        enhanced_query = f"PROBLEMA: {query}"
        
        # Buscar
        results = self.collection.query(
            query_texts=[enhanced_query],
            n_results=n_results,
            where=filter_metadata
        )
        
        documents = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None,
                    "relevance_score": 1 - (results['distances'][0][i] if results['distances'] else 0)
                })
        
        return documents
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da base de conhecimento"""
        total = self.collection.count()
        
        # Buscar todos os metadados para estatísticas
        if total > 0:
            all_data = self.collection.get()
            metadatas = all_data['metadatas']
            
            # Contar por tipo
            types = {}
            with_questions = 0
            with_steps = 0
            
            for meta in metadatas:
                ticket_type = meta.get('type', 'Desconhecido')
                types[ticket_type] = types.get(ticket_type, 0) + 1
                
                if meta.get('has_questions') == 'sim':
                    with_questions += 1
                if meta.get('has_steps') == 'sim':
                    with_steps += 1
            
            return {
                "total_documents": total,
                "with_questions": with_questions,
                "with_steps": with_steps,
                "types": types
            }
        
        return {"total_documents": 0}


# Instância global
_rag_instance = None


def get_rag_instance() -> KnowledgeBaseRAG:
    """Retorna instância singleton do RAG"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = KnowledgeBaseRAG()
    return _rag_instance


def search_knowledge_base(query: str, num_results: int = 5) -> str:
    """
    Busca informações na base de conhecimento técnica.
    OTIMIZADO: Busca em tickets históricos resolvidos
    ATUALIZADO: Top 5 resultados com logs detalhados
    
    Args:
        query: Descrição do problema ou pergunta técnica
        num_results: Número de resultados a retornar (padrão: 5)
    
    Returns:
        String formatada com os resultados encontrados
    """
    # Log início da busca RAG
    agent_logger.info("\n" + "="*70)
    agent_logger.info("🔍 RAG INICIADO")
    agent_logger.info("="*70)
    agent_logger.info(f"📝 Query: '{query}'")
    agent_logger.info(f"🎯 Top: {num_results} resultados")
    
    rag = get_rag_instance()
    results = rag.search_knowledge(query, n_results=num_results)
    
    if not results:
        agent_logger.warning("⚠️  RAG: Nenhum resultado encontrado")
        agent_logger.info(f"📊 Tamanho do conteúdo retornado: 0 caracteres")
        agent_logger.info("="*70 + "\n")
        return "Não encontrei soluções similares na base de conhecimento para este problema específico."
    
    # Log de sucesso
    agent_logger.info(f"✅ RAG: Encontrados {len(results)} resultados relevantes")
    
    # Formatar resultados
    formatted_results = "📚 **Casos Similares Encontrados na Base de Conhecimento:**\n\n"
    
    total_chars = 0
    for i, result in enumerate(results, 1):
        content = result['content']
        metadata = result.get('metadata', {})
        relevance = result.get('relevance_score', 0) * 100
        
        # Contar caracteres
        result_text = f"**Caso {i}** (Relevância: {relevance:.0f}%)\n"
        total_chars += len(result_text)
        
        formatted_results += result_text
        
        # Mostrar metadados estruturados
        if metadata.get('name'):
            line = f"📋 **Nome:** {metadata['name']}\n"
            formatted_results += line
            total_chars += len(line)
        
        if metadata.get('type'):
            line = f"🏷️ **Tipo:** {metadata['type']}\n"
            formatted_results += line
            total_chars += len(line)
        
        # Extrair descrição do content se houver
        if "Descrição:" in content:
            description = content.split("Descrição:")[1].split("|")[0].strip()
            if description:
                line = f"📝 **Descrição:** {description[:300]}{'...' if len(description) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)
        
        # Extrair perguntas do content se houver
        if "Perguntas:" in content:
            questions = content.split("Perguntas:")[1].split("|")[0].strip()
            if questions:
                line = f"❓ **Perguntas:** {questions[:300]}{'...' if len(questions) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)
        
        # Extrair passos do content se houver
        if "Passos:" in content:
            steps = content.split("Passos:")[1].split("|")[0].strip() if "|" in content.split("Passos:")[1] else content.split("Passos:")[1].strip()
            if steps:
                line = f"📋 **Passos:** {steps[:300]}{'...' if len(steps) > 300 else ''}\n"
                formatted_results += line
                total_chars += len(line)
        
        formatted_results += "\n"
        total_chars += 1
        
        # Log individual de cada resultado
        agent_logger.info(f"   • Resultado {i}: {metadata.get('name', 'N/A')[:50]} - Relevância: {relevance:.0f}%")
    
    formatted_results += "💡 **Sugestão:** Use essas soluções como base para resolver o problema atual.\n"
    total_chars += len("💡 **Sugestão:** Use essas soluções como base para resolver o problema atual.\n")
    
    # Log final com estatísticas
    agent_logger.info(f"\n📊 ESTATÍSTICAS DO RAG:")
    agent_logger.info(f"   • Resultados retornados: {len(results)}")
    agent_logger.info(f"   • Tamanho total do conteúdo: {total_chars:,} caracteres")
    agent_logger.info(f"   • Média por resultado: {total_chars // len(results):,} caracteres")
    
    # Relevância média
    avg_relevance = sum(r.get('relevance_score', 0) for r in results) / len(results) * 100
    agent_logger.info(f"   • Relevância média: {avg_relevance:.1f}%")
    
    agent_logger.info("="*70 + "\n")
    
    return formatted_results


def load_knowledge_from_csv(csv_path: str, force_reload: bool = False):
    """
    Função helper para carregar base de conhecimento de CSV
    Use isso no seu script principal ou setup
    
    Args:
        csv_path: Caminho para o CSV de tickets
        force_reload: Se True, limpa base existente e recarrega
    
    Example:
        >>> from rag_system import load_knowledge_from_csv
        >>> load_knowledge_from_csv("tickets_historicos.csv")
    """
    rag = get_rag_instance()
    rag.load_tickets_from_csv(csv_path, force_reload=force_reload)


def show_rag_stats():
    """Mostra estatísticas da base de conhecimento"""
    rag = get_rag_instance()
    stats = rag.get_stats()
    
    print("\n" + "="*60)
    print("📊 ESTATÍSTICAS DA BASE DE CONHECIMENTO")
    print("="*60)
    print(f"📚 Total de documentos: {stats.get('total_documents', 0)}")
    print(f"❓ Com perguntas: {stats.get('with_questions', 0)}")
    print(f"📝 Com passos: {stats.get('with_steps', 0)}")
    
    if 'types' in stats and stats['types']:
        print(f"\n📁 Distribuição por tipo:")
        for ticket_type, count in sorted(stats['types'].items(), key=lambda x: x[1], reverse=True):
            print(f"   • {ticket_type}: {count} registros")
    
    print("="*60 + "\n")