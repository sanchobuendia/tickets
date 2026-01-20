"""
Script para criar uma única collection no ChromaDB chamada "codigo"
Carrega todos os dados do CSV em uma collection
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import pandas as pd
import os


class SingleCollectionManager:
    """Gerencia uma única collection no ChromaDB"""
    
    def __init__(self, chroma_persist_directory: str = "./chroma_db", 
                 embedding_model: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Inicializa o gerenciador de collection
        
        Args:
            chroma_persist_directory: Diretório para persistir os dados do ChromaDB
            embedding_model: Modelo de embeddings a ser usado
        """
        # Criar diretório se não existir
        os.makedirs(chroma_persist_directory, exist_ok=True)
        
        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(
            path=chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Modelo de embeddings
        self.embedding_model = SentenceTransformer(embedding_model)
        
        print(f"✅ ChromaDB inicializado")
        print(f"📁 Diretório: {chroma_persist_directory}")
    
    def load_data_from_csv(self, csv_path: str, collection_name: str = "codigo", force_reload: bool = False):
        """
        Carrega dados do CSV em uma única collection
        
        Args:
            csv_path: Caminho para o arquivo CSV
            collection_name: Nome da collection (padrão: "codigo")
            force_reload: Se True, limpa a collection e recarrega
        """
        print("\n" + "="*70)
        print("📂 CARREGANDO DADOS DO CSV")
        print("="*70)
        print(f"📄 Arquivo: {csv_path}")
        print(f"📚 Collection: {collection_name}")
        
        try:
            # Ler CSV
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
            print(f"✅ CSV carregado: {len(df)} registros encontrados")
            
            # Se force_reload, limpar collection existente
            if force_reload:
                try:
                    print("\n🗑️  Limpando collection existente...")
                    self.client.delete_collection(collection_name)
                    print(f"   ❌ Collection '{collection_name}' deletada")
                except:
                    print(f"   ℹ️  Collection '{collection_name}' não existia")
            
            # Criar ou obter collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Base de conhecimento de códigos"}
            )
            
            # Verificar se já tem documentos e não é reload
            if collection.count() > 0 and not force_reload:
                print(f"\n⏭️  Collection já contém {collection.count()} documentos.")
                print(f"   Use force_reload=True para recarregar.")
                return
            
            print("\n📝 ADICIONANDO DOCUMENTOS À COLLECTION:")
            print("-" * 70)
            
            # Adicionar documentos
            added_count = 0
            skipped_count = 0
            
            for idx, row in df.iterrows():
                try:
                    # Extrair informações
                    grupo_solucao = str(row['Descrição do grupo de solução']) if pd.notna(row['Descrição do grupo de solução']) else ""
                    desc_completa = str(row['Descrição completa']) if pd.notna(row['Descrição completa']) else ""
                    descricao = str(row['Descrição']) if pd.notna(row['Descrição']) else ""
                    codigo_grupo = str(row['Código do grupo de solução']) if pd.notna(row['Código do grupo de solução']) else ""
                    codigo_categoria = str(row['Código da categoria']) if pd.notna(row['Código da categoria']) else ""
                    
                    # Pular se não tem informação útil
                    if not desc_completa and not descricao and not grupo_solucao:
                        skipped_count += 1
                        continue
                    
                    # Criar conteúdo concatenado
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
                    
                    # Metadados
                    metadata = {
                        "grupo_solucao": grupo_solucao,
                        "descricao_completa": desc_completa[:500] if desc_completa else "",
                        "descricao": descricao[:200] if descricao else "",
                        "codigo_grupo": codigo_grupo,
                        "codigo_categoria": codigo_categoria
                    }
                    
                    # Adicionar à collection
                    doc_id = f"doc_{codigo_categoria}_{idx}"
                    collection.add(
                        ids=[doc_id],
                        documents=[content],
                        metadatas=[metadata]
                    )
                    
                    added_count += 1
                    
                    # Log a cada 100 documentos
                    if added_count % 100 == 0:
                        print(f"   📝 Processados: {added_count} documentos...")
                    
                except Exception as e:
                    print(f"   ⚠️  Erro ao processar linha {idx}: {e}")
                    skipped_count += 1
                    continue
            
            # Resumo final
            print("\n" + "="*70)
            print("📊 RESUMO DA OPERAÇÃO")
            print("="*70)
            print(f"✅ Documentos adicionados: {added_count}")
            print(f"⏭️  Documentos pulados: {skipped_count}")
            print(f"📚 Total na collection: {collection.count()}")
            print("="*70 + "\n")
            
        except FileNotFoundError:
            print(f"❌ Arquivo não encontrado: {csv_path}")
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            import traceback
            traceback.print_exc()
    
    def get_collection_stats(self, collection_name: str = "codigo"):
        """
        Retorna estatísticas da collection
        
        Args:
            collection_name: Nome da collection
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            collection = self.client.get_collection(collection_name)
            
            total = collection.count()
            
            if total > 0:
                # Buscar todos os metadados para estatísticas
                all_data = collection.get()
                metadatas = all_data['metadatas']
                
                # Contar por grupo de solução
                grupos = {}
                for meta in metadatas:
                    grupo = meta.get('grupo_solucao', 'Desconhecido')
                    grupos[grupo] = grupos.get(grupo, 0) + 1
                
                return {
                    "collection_name": collection_name,
                    "total_documentos": total,
                    "grupos": grupos
                }
            
            return {
                "collection_name": collection_name,
                "total_documentos": 0
            }
        
        except Exception as e:
            return {"erro": str(e)}
    
    def search(self, query: str, collection_name: str = "codigo", n_results: int = 5, filter_grupo: str = None):
        """
        Busca na collection
        
        Args:
            query: Query de busca
            collection_name: Nome da collection
            n_results: Número de resultados
            filter_grupo: Filtrar por grupo específico (opcional)
        
        Returns:
            Lista de documentos encontrados
        """
        try:
            collection = self.client.get_collection(collection_name)
            
            # Preparar filtro se especificado
            where_filter = None
            if filter_grupo:
                where_filter = {"grupo_solucao": filter_grupo}
            
            # Realizar busca
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            documents = []
            if results and results['documents']:
                for i in range(len(results['documents'][0])):
                    documents.append({
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None
                    })
            
            return documents
        
        except Exception as e:
            print(f"❌ Erro ao buscar: {e}")
            return []


def main():
    """Função principal para executar o script"""
    
    # Configurações
    CSV_PATH = "codigos.csv"  # Ajuste o caminho conforme necessário
    CHROMA_DIR = "./chroma_db"
    COLLECTION_NAME = "codigo"
    FORCE_RELOAD = False  # Mude para True para recarregar tudo
    
    print("\n" + "="*70)
    print("🚀 INICIANDO CRIAÇÃO DA COLLECTION")
    print("="*70)
    
    # Criar gerenciador
    manager = SingleCollectionManager(
        chroma_persist_directory=CHROMA_DIR,
        embedding_model='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    )
    
    # Carregar dados
    manager.load_data_from_csv(CSV_PATH, collection_name=COLLECTION_NAME, force_reload=FORCE_RELOAD)
    
    # Mostrar estatísticas
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS DA COLLECTION")
    print("="*70)
    
    stats = manager.get_collection_stats(COLLECTION_NAME)
    
    if "erro" in stats:
        print(f"❌ Erro: {stats['erro']}")
    else:
        print(f"📚 Collection: {stats['collection_name']}")
        print(f"📝 Total de documentos: {stats['total_documentos']}")
        
        if 'grupos' in stats and stats['grupos']:
            print(f"\n📁 Distribuição por grupo de solução:")
            for grupo, count in sorted(stats['grupos'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   • {grupo}: {count} documentos")
            
            if len(stats['grupos']) > 10:
                print(f"   ... e mais {len(stats['grupos']) - 10} grupos")
    
    print("="*70)
    print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    print("="*70 + "\n")
    
    # Exemplo de uso
    print("\n💡 EXEMPLO DE USO:")
    print("-" * 70)
    print("# Para buscar na collection:")
    print("results = manager.search('problema com impressora', n_results=5)")
    print("\n# Para buscar filtrando por grupo:")
    print("results = manager.search('impressora', filter_grupo='Help Desk', n_results=3)")
    print("\n# Para ver estatísticas:")
    print("stats = manager.get_collection_stats()")
    print("-" * 70 + "\n")


if __name__ == "__main__":
    main()