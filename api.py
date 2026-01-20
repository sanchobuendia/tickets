# uvicorn api:app --reload --host 0.0.0.0 --port 8000
# python api.py
"""
API REST para o Chatbot de Suporte Técnico
Permite integração com outras aplicações
"""
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar credenciais AWS ANTES de qualquer import que use AWS
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-1")
os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

# Remover AWS_PROFILE para evitar conflitos
if "AWS_PROFILE" in os.environ:
    del os.environ["AWS_PROFILE"]

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
from orchestrator import create_orchestrator_agent, ConversationState
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from rag_system import KnowledgeBaseRAG
import uuid

app = FastAPI(
    title="Tech Support Chatbot API",
    description="""
    ## 🤖 API para Chatbot Multi-Agente de Suporte Técnico
    
    Sistema inteligente que usa **Google ADK + Claude (AWS Bedrock)** para atendimento técnico automatizado.
    
    ### Funcionalidades:
    - ✅ Suporte técnico automatizado
    - ✅ Base de conhecimento com RAG
    - ✅ Criação e fechamento de tickets
    - ✅ Sessões de conversação persistentes
    
    ### Como usar:
    1. Crie uma sessão com `POST /session`
    2. Envie mensagens com `POST /chat` usando o `session_id`
    3. Consulte o estado com `GET /session/{session_id}`
    
    ### Tecnologias:
    - Google ADK (Agent Development Kit)
    - Claude 3.5 Sonnet (AWS Bedrock)
    - ChromaDB (Vector Database)
    - FastAPI
    """,
    version="1.0.0",
    contact={
        "name": "Suporte Técnico",
        "email": "suporte@exemplo.com",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "Chat",
            "description": "Endpoints para interação com o chatbot"
        },
        {
            "name": "Session",
            "description": "Gerenciamento de sessões de conversação"
        },
        {
            "name": "Health",
            "description": "Endpoints de monitoramento"
        }
    ]
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Armazenamento de sessões em memória
sessions: Dict[str, Dict[str, Any]] = {}


class MessageRequest(BaseModel):
    """Modelo de requisição de mensagem"""
    message: str = Field(
        ..., 
        description="Mensagem do usuário",
        examples=["Meu computador está lento", "Não consigo imprimir", "Internet não funciona"]
    )
    session_id: Optional[str] = Field(
        None, 
        description="ID da sessão (opcional - cria nova se não fornecido)",
        examples=["13012026-test001"]
    )


class MessageResponse(BaseModel):
    """Modelo de resposta de mensagem"""
    response: str = Field(
        ..., 
        description="Resposta do chatbot",
        examples=["Vou te ajudar a resolver esse problema. Primeiro, vamos verificar..."]
    )
    session_id: str = Field(
        ..., 
        description="ID da sessão",
        examples=["13012026-test001"]
    )
    state: Dict[str, Any] = Field(
        ..., 
        description="Estado da conversa"
    )


class SessionResponse(BaseModel):
    """Modelo de resposta de sessão"""
    session_id: str = Field(
        ...,
        description="ID único da sessão criada",
        examples=["13012026-test001"]
    )
    created: bool = Field(
        ...,
        description="Indica se a sessão foi criada com sucesso",
        examples=[True]
    )


async def get_or_create_session(session_id: Optional[str] = None) -> tuple:
    """
    Obtém uma sessão existente ou cria uma nova
    
    Returns:
        Tupla (session_id, runner, state, is_new)
    """
    if session_id and session_id in sessions:
        session_data = sessions[session_id]
        return (
            session_id,
            session_data["runner"],
            session_data["state"],
            False
        )
    
    # Criar nova sessão
    new_session_id = session_id or str(uuid.uuid4())
    
    # Criar componentes
    orchestrator = create_orchestrator_agent()
    session_service = InMemorySessionService()
    
    # CORREÇÃO: create_session é assíncrona
    session = await session_service.create_session(
        app_name=orchestrator.name,
        session_id="tech_support_session",
        user_id="user_123"
    )
    
    runner = Runner(
        app_name=orchestrator.name,
        agent=orchestrator,
        session_service=session_service
    )
    
    state = ConversationState()
    
    # Armazenar sessão
    sessions[new_session_id] = {
        "runner": runner,
        "state": state,
        "session": session,
        "session_id": session.id
    }
    
    return new_session_id, runner, state, True


@app.on_event("startup")
async def startup_event():
    """Inicializa o sistema ao iniciar a API"""
    print("🚀 Iniciando API do Chatbot de Suporte Técnico...")
    
    # Inicializar base de conhecimento
    rag = KnowledgeBaseRAG()
    print("✅ Base de conhecimento carregada")
    
    print("✅ API pronta para receber requisições!")


@app.get("/", tags=["Health"])
async def root():
    """
    ## Endpoint Raiz
    
    Retorna informações sobre a API e endpoints disponíveis.
    
    **Resposta:**
    - Informações da API
    - Lista de endpoints disponíveis
    - Status online
    """
    return {
        "message": "Tech Support Chatbot API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "POST /chat": "Enviar mensagem para o chatbot",
            "POST /session": "Criar nova sessão",
            "GET /session/{session_id}": "Obter estado da sessão",
            "DELETE /session/{session_id}": "Deletar sessão",
            "GET /health": "Verificar saúde da API"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    ## Health Check
    
    Verifica se a API está funcionando corretamente.
    
    **Retorna:**
    - Status da API
    - Número de sessões ativas
    """
    return {
        "status": "healthy",
        "active_sessions": len(sessions)
    }


@app.post("/session", response_model=SessionResponse, tags=["Session"])
async def create_session():
    """
    ## Criar Nova Sessão
    
    Cria uma nova sessão de conversação com o chatbot.
    
    **Como funciona:**
    - Gera um ID único para a sessão
    - Inicializa os agentes especializados
    - Cria contexto isolado para a conversa
    
    **Importante:**
    - Guarde o `session_id` retornado
    - Use este ID em todas as chamadas `/chat`
    - Cada sessão mantém seu próprio histórico
    
    **Exemplo de resposta:**
    ```json
    {
      "session_id": "13012026-test001",
      "created": true
    }
    ```
    """
    session_id = str(uuid.uuid4())
    _, _, _, is_new = await get_or_create_session(session_id)
    
    return {
        "session_id": session_id,
        "created": is_new
    }


@app.get("/session/{session_id}", tags=["Session"])
async def get_session_state(session_id: str):
    """
    ## Obter Estado da Sessão
    
    Retorna informações sobre o estado atual de uma sessão.
    
    **Informações retornadas:**
    - ID do ticket (se criado)
    - Status do problema (resolvido ou não)
    - Nome do usuário
    - Descrição do problema
    - Notas de resolução
    - Número de mensagens trocadas
    
    **Útil para:**
    - Debugar conversas
    - Monitorar progresso
    - Integração com outros sistemas
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    state = sessions[session_id]["state"]
    return {
        "session_id": session_id,
        "state": state.get_summary()
    }


@app.delete("/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
    """
    ## Deletar Sessão
    
    Remove uma sessão e libera recursos.
    
    **Quando usar:**
    - Ao final de uma conversa
    - Para limpar sessões antigas
    - Para liberar memória
    
    **Atenção:**
    - Esta ação é irreversível
    - Todo histórico será perdido
    - Crie uma nova sessão se precisar conversar novamente
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    del sessions[session_id]
    return {
        "message": "Sessão deletada com sucesso",
        "session_id": session_id
    }


@app.post("/chat", response_model=MessageResponse, tags=["Chat"])
async def chat(request: MessageRequest):
    """
    ## Enviar Mensagem para o Chatbot
    
    Envia uma mensagem e recebe resposta do sistema multi-agente.
    
    **Como funciona:**
    1. Mensagem é processada pelo agente orquestrador
    2. Orquestrador delega para agentes especializados:
       - Agente de Suporte (resolve diretamente)
       - Agente RAG (busca na base de conhecimento)
       - Agente de Tickets (cria/fecha chamados)
    3. Resposta é retornada com contexto atualizado
    
    **Parâmetros:**
    - `message`: Sua mensagem/problema
    - `session_id`: ID da sessão (opcional - cria nova se não fornecido)
    
    **Exemplos de mensagens:**
    - "Meu computador está muito lento"
    - "Não consigo conectar na internet"
    - "A impressora não está funcionando"
    - "Esqueci minha senha do Windows"
    
    **Resposta inclui:**
    - Resposta do chatbot
    - ID da sessão
    - Estado atualizado da conversa
    
    **Exemplo de requisição:**
    ```json
    {
      "message": "Meu computador está lento e travando",
      "session_id": "13012026-test001"
    }
    ```
    
    **Exemplo de resposta:**
    ```json
    {
      "response": "Entendi que seu computador está lento. Vou te ajudar...",
      "session_id": "13012026-test001",
      "state": {
        "ticket_id": null,
        "problem_resolved": false,
        "user_name": null,
        "messages_count": 2
      }
    }
    ```
    """
    try:
        # Obter ou criar sessão
        session_id, runner, state, is_new = await get_or_create_session(request.session_id)
        
        # Adicionar mensagem ao histórico
        state.add_message("user", request.message)
        
        # Obter sessão do ADK
        adk_session_id = sessions[session_id]["session_id"]
        
        # Criar mensagem como dict ou objeto apropriado
        # CORREÇÃO: testar diferentes formatos de mensagem
        try:
            # Tentar importar Message dinamicamente
            from google.genai.types import Content, Part
            message_obj = Content(role="user", parts=[Part(text=request.message)])
        except:
            # Se não funcionar, tentar como dict simples
            message_obj = {"role": "user", "content": request.message}
        
        # Executar agente - capturar resposta do generator corretamente
        bot_response = ""
        response_chunks = []
        
        for chunk in runner.run(
            new_message=message_obj,
            session_id=adk_session_id,
            user_id="user_123"
        ):
            response_chunks.append(chunk)
            
            # Tentar extrair conteúdo de diferentes formatos
            if hasattr(chunk, 'content'):
                content = chunk.content
                # Se content é string, usar diretamente
                if isinstance(content, str):
                    bot_response = content
                # Se content tem parts (Content do google.genai)
                elif hasattr(content, 'parts') and content.parts:
                    # Extrair texto do primeiro part
                    first_part = content.parts[0]
                    if hasattr(first_part, 'text'):
                        bot_response = first_part.text
                    else:
                        bot_response = str(first_part)
                else:
                    bot_response = str(content)
            elif hasattr(chunk, 'parts'):
                # Chunk é um Content diretamente
                if chunk.parts:
                    first_part = chunk.parts[0]
                    if hasattr(first_part, 'text'):
                        bot_response = first_part.text
                    else:
                        bot_response = str(first_part)
            elif hasattr(chunk, 'text'):
                bot_response = chunk.text
            elif hasattr(chunk, 'message'):
                bot_response = chunk.message
            elif isinstance(chunk, dict):
                bot_response = chunk.get("content") or chunk.get("text") or chunk.get("message") or chunk.get("response", "")
            elif isinstance(chunk, str):
                bot_response = chunk
        
        # Se ainda não temos resposta, tentar converter o último chunk
        if not bot_response and response_chunks:
            last_chunk = response_chunks[-1]
            if hasattr(last_chunk, 'parts') and last_chunk.parts:
                first_part = last_chunk.parts[0]
                if hasattr(first_part, 'text'):
                    bot_response = first_part.text
        
        if not bot_response:
            bot_response = "Desculpe, não consegui processar sua mensagem."
        
        # Adicionar ao histórico
        state.add_message("assistant", bot_response)
        
        return {
            "response": bot_response,
            "session_id": session_id,
            "state": state.get_summary()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: MessageRequest):
    """
    Endpoint para chat com streaming (para implementação futura)
    """
    raise HTTPException(
        status_code=501,
        detail="Streaming não implementado ainda"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )