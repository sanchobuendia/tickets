# uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""
API REST para o Chatbot de Suporte Técnico
🔥 CORRIGIDO: Usa user_id ao invés de session_id
🔥 NOVO: Suporta múltiplos problemas por mensagem
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar credenciais AWS
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-1")
os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

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
    
    🔥 **ATUALIZADO**: Usa `user_id` para controle de sessão (não session_id)
    🔥 **NOVO**: Suporta múltiplos problemas na mesma mensagem
    
    ### Funcionalidades:
    - ✅ Suporte técnico automatizado
    - ✅ Base de conhecimento com RAG
    - ✅ Criação de tickets (um por problema)
    - ✅ Reset de contexto após cada atendimento
    - ✅ Múltiplos problemas processados individualmente
    
    ### Como usar:
    1. Envie mensagens com `POST /chat` usando seu `user_id`
    2. Sistema identifica múltiplos problemas automaticamente
    3. Cada problema gera um ticket separado
    4. Após processar todos, contexto é resetado
    
    ### Tecnologias:
    - Google ADK (Agent Development Kit)
    - Claude 3.5 Sonnet (AWS Bedrock)
    - ChromaDB (Vector Database)
    - FastAPI
    """,
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 MUDANÇA: Armazenar por user_id ao invés de session_id
user_sessions: Dict[str, Dict[str, Any]] = {}


class MessageRequest(BaseModel):
    """Modelo de requisição de mensagem"""
    message: str = Field(
        ..., 
        description="Mensagem do usuário (pode conter múltiplos problemas)",
        examples=[
            "Quero reservar uma sala, meu computador nao liga e a imporessora está atolada", 
            "PC lento E impressora travada E email não abre"
        ]
    )
    user_id: str = Field(  # 🔥 MUDOU: session_id → user_id
        ..., 
        description="ID único do usuário (telefone, email, etc)",
        examples=["5531999887766", "user@empresa.com", "user_123"]
    )


class MessageResponse(BaseModel):
    """Modelo de resposta de mensagem"""
    response: str = Field(..., description="Resposta do chatbot")
    user_id: str = Field(..., description="ID do usuário")  # 🔥 MUDOU
    tickets_created: int = Field(  # 🔥 NOVO: quantos tickets foram criados
        default=0,
        description="Número de tickets criados nesta interação"
    )
    state: Dict[str, Any] = Field(..., description="Estado da conversa")


async def get_or_create_user_session(user_id: str) -> tuple:
    """
    Obtém sessão do usuário ou cria nova
    🔥 MUDANÇA: Agora usa user_id como chave principal
    
    Args:
        user_id: ID único do usuário
        
    Returns:
        Tupla (user_id, runner, state, is_new)
    """
    if user_id in user_sessions:
        session_data = user_sessions[user_id]
        return (
            user_id,
            session_data["runner"],
            session_data["state"],
            False
        )
    
    # Criar nova sessão para este usuário
    orchestrator = create_orchestrator_agent()
    session_service = InMemorySessionService()
    
    # Sessão do ADK (framework)
    adk_session = await session_service.create_session(
        app_name=orchestrator.name,
        session_id=f"adk_{user_id}_{str(uuid.uuid4())[:8]}",  # Sessão interna do ADK
        user_id=user_id  # 🔥 Mas vinculada ao user_id
    )
    
    runner = Runner(
        app_name=orchestrator.name,
        agent=orchestrator,
        session_service=session_service
    )
    
    # Estado COM user_id
    state = ConversationState(user_id=user_id)  # 🔥 IMPORTANTE
    
    # Armazenar por user_id
    user_sessions[user_id] = {
        "runner": runner,
        "state": state,
        "adk_session": adk_session,
        "user_id": user_id
    }
    
    return user_id, runner, state, True


@app.on_event("startup")
async def startup_event():
    """Inicializa o sistema"""
    print("🚀 Iniciando API do Chatbot de Suporte Técnico...")
    
    # Inicializar base de conhecimento
    rag = KnowledgeBaseRAG()
    print("✅ Base de conhecimento carregada")
    
    print("✅ API pronta para receber requisições!")


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Tech Support Chatbot API v2.0",
        "version": "2.0.0",
        "status": "online",
        "changes": {
            "v2.0": [
                "🔥 Usa user_id ao invés de session_id",
                "🔥 Suporta múltiplos problemas por mensagem",
                "🔥 Reset automático de contexto após tickets",
                "🔥 Um ticket por problema identificado"
            ]
        },
        "endpoints": {
            "POST /chat": "Enviar mensagem (use user_id)",
            "GET /user/{user_id}/state": "Obter estado do usuário",
            "DELETE /user/{user_id}": "Limpar sessão do usuário",
            "GET /health": "Verificar saúde da API"
        }
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "active_users": len(user_sessions)  # 🔥 MUDOU: active_users
    }


@app.get("/user/{user_id}/state")  # 🔥 NOVO endpoint
async def get_user_state(user_id: str):
    """
    Obter estado atual de um usuário
    
    Args:
        user_id: ID do usuário
    """
    if user_id not in user_sessions:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    
    state = user_sessions[user_id]["state"]
    return {
        "user_id": user_id,
        "state": state.get_summary()
    }


@app.delete("/user/{user_id}")  # 🔥 MUDOU: session → user
async def delete_user_session(user_id: str):
    """
    Deletar sessão de um usuário
    
    Args:
        user_id: ID do usuário
    """
    if user_id not in user_sessions:
        raise HTTPException(status_code=404, detail=f"Usuário {user_id} não encontrado")
    
    del user_sessions[user_id]
    return {
        "message": "Sessão deletada com sucesso",
        "user_id": user_id
    }


@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """
    Enviar mensagem para o chatbot
    
    🔥 ATUALIZADO:
    - Usa user_id ao invés de session_id
    - Suporta múltiplos problemas na mesma mensagem
    - Cria um ticket para cada problema
    - Reseta contexto após processar todos os problemas
    
    Exemplo de mensagem com múltiplos problemas:
    ```json
    {
      "message": "PC lento E impressora travada E email não abre",
      "user_id": "5531999887766"
    }
    ```
    
    Resultado esperado:
    - 3 problemas identificados
    - 3 tickets criados (um para cada)
    - Contexto resetado após processar todos
    """
    try:
        # Obter ou criar sessão do usuário
        user_id, runner, state, is_new = await get_or_create_user_session(request.user_id)
        
        # 🔥 VERIFICAR SE DEVE RESETAR CONTEXTO
        if state.should_reset_context():
            print(f"🔄 RESET de contexto para usuário {user_id}")
            state.clear_history_except_current()
        
        # Adicionar mensagem ao histórico
        state.add_message("user", request.message)
        
        # Obter sessão do ADK
        adk_session = user_sessions[user_id]["adk_session"]
        
        # Criar mensagem
        try:
            from google.genai.types import Content, Part
            message_obj = Content(role="user", parts=[Part(text=request.message)])
        except:
            message_obj = {"role": "user", "content": request.message}
        
        # 🔥 IMPORTANTE: Contar tickets antes
        from tools import ticket_api_client, set_current_user_id
        
        # 🔥 NOVO: Definir user_id no contexto antes de executar
        set_current_user_id(user_id)
        
        tickets_before = len(ticket_api_client.local_cache)
        
        # Executar agente
        bot_response = ""
        response_chunks = []
        
        for chunk in runner.run(
            new_message=message_obj,
            session_id=adk_session.id,
            user_id=user_id  # 🔥 PASSA user_id para o runner
        ):
            response_chunks.append(chunk)
            
            if hasattr(chunk, 'content'):
                content = chunk.content
                if isinstance(content, str):
                    bot_response = content
                elif hasattr(content, 'parts') and content.parts:
                    first_part = content.parts[0]
                    if hasattr(first_part, 'text'):
                        bot_response = first_part.text
                    else:
                        bot_response = str(first_part)
                else:
                    bot_response = str(content)
            elif hasattr(chunk, 'parts'):
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
        
        if not bot_response and response_chunks:
            last_chunk = response_chunks[-1]
            if hasattr(last_chunk, 'parts') and last_chunk.parts:
                first_part = last_chunk.parts[0]
                if hasattr(first_part, 'text'):
                    bot_response = first_part.text
        
        if not bot_response:
            bot_response = "Desculpe, não consegui processar sua mensagem."
        
        # Adicionar resposta ao histórico
        state.add_message("assistant", bot_response)
        
        # 🔥 CONTAR quantos tickets foram criados
        tickets_after = len(ticket_api_client.local_cache)
        tickets_created = tickets_after - tickets_before
        
        return {
            "response": bot_response,
            "user_id": user_id,
            "tickets_created": tickets_created,  # 🔥 NOVO
            "state": state.get_summary()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )