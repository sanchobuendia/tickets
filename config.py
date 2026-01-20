"""
Configurações do sistema
"""
import os
from dotenv import load_dotenv
import litellm

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# ⚠️ IMPORTANTE: Desabilitar logging assíncrono do LiteLLM
# Isso previne o erro: "Queue is bound to a different event loop"
litellm.turn_off_message_logging = True
litellm.suppress_debug_info = True
litellm.drop_params = True  # Drop parâmetros não suportados sem erro

# ⚠️ IMPORTANTE: Configurações para Bedrock
# Previne warnings sobre consecutive user/tool blocks
litellm.modify_params = True  # Permite LiteLLM modificar parâmetros automaticamente
litellm.set_verbose = False  # Desabilita logs verbosos

# Suprimir warnings de asyncio/event loop (não afetam funcionalidade)
import warnings
warnings.filterwarnings("ignore", message=".*Queue.*different event loop.*")
warnings.filterwarnings("ignore", category=RuntimeWarning)


class Config:
    """Configurações centralizadas do sistema"""
    
    # AWS Bedrock Configuration
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    # Claude Model no Bedrock
    # Formato correto para LiteLLM: bedrock/MODEL_ID (sem região no ID)
    # O modelo ID correto para Bedrock usa o prefixo da região: us.anthropic ou apenas anthropic
    BEDROCK_CLAUDE_MODEL = "bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    # Modelos alternativos disponíveis:
    # BEDROCK_CLAUDE_MODEL = "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0"  # Sonnet 3.5 v2
    # BEDROCK_CLAUDE_MODEL = "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"    # Sonnet 3
    # BEDROCK_CLAUDE_MODEL = "bedrock/anthropic.claude-3-haiku-20240307-v1:0"     # Haiku 3
    
    # Modelo de Embeddings para RAG
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Configurações do modelo Claude
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))  # 0.0 = mais determinístico, 1.0 = mais criativo
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
    
    # API de Tickets (JSONPlaceholder como exemplo)
    TICKET_API_BASE_URL = "https://jsonplaceholder.typicode.com"
    
    # Configurações do ChromaDB
    CHROMA_PERSIST_DIRECTORY = "./chroma_db"
    CHROMA_COLLECTION_NAME = "tech_support_kb"
    
    @classmethod
    def validate(cls):
        """Valida se as configurações necessárias estão presentes"""
        if not cls.AWS_ACCESS_KEY_ID:
            raise ValueError("AWS_ACCESS_KEY_ID não configurado no .env")
        if not cls.AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS_SECRET_ACCESS_KEY não configurado no .env")
        
        print("✅ Configurações AWS validadas")
        print(f"   Região: {cls.AWS_REGION}")
        print(f"   Modelo: {cls.BEDROCK_CLAUDE_MODEL}")
    
    @classmethod
    def get_aws_credentials(cls):
        """Retorna credenciais AWS como dicionário"""
        return {
            "aws_access_key_id": cls.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": cls.AWS_SECRET_ACCESS_KEY,
            "aws_region_name": cls.AWS_REGION
        }


# Validar configurações ao importar
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"⚠️  Aviso de configuração: {e}")