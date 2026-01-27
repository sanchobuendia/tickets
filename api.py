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
from typing import Optional, Dict, Any, List
import asyncio
from orchestrator import create_orchestrator_agent, ConversationState
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from rag import KnowledgeBaseRAG
import uuid
from logger import agent_logger
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from config import Config

api_log = agent_logger.with_prefix("API")

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
    userId: str = Field(
        ..., 
        description="ID único do usuário (telefone, email, etc)",
        examples=["5531999887766", "user@empresa.com", "user_123"]
    )
    message: str = Field(
        ..., 
        description="Mensagem do usuário (pode conter múltiplos problemas)",
        examples=[
            "Quero reservar uma sala, meu computador nao liga e a imporessora está atolada", 
            "PC lento E impressora travada E email não abre"
        ]
    )
    attachments: List[str] = Field(
        default_factory=list,
        description="Lista de caminhos no S3 para anexos",
        examples=[["path-1", "path-2"]]
    )
    class Config:
        json_schema_extra = {
            "example": {
                "userId": "789",
                "message": "mensagem para a IA",
                "attachments": ["s3://meu-bucket/path-1", "s3://meu-bucket/path-2"]
            }
        }


class TicketResponse(BaseModel):
    pending: bool
    title: str
    description: str
    groupCode: str
    categoryCode: str
    attachments: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "pending": False,
                "title": "Issue with login",
                "description": "User cannot log in to the system.",
                "groupCode": "456",
                "categoryCode": "123",
                "attachments": ["path-1", "path-2"],
            }
        }


class MessageResponse(BaseModel):
    """Modelo de resposta de mensagem"""
    userId: str = Field(..., description="ID do usuário")
    message: str = Field(..., description="Resposta do chatbot")
    tickets: List[TicketResponse] = Field(default_factory=list)
    class Config:
        json_schema_extra = {
            "example": {
                "userId": "789",
                "message": "mensagem para o user",
                "tickets": [
                    {
                        "pending": False,
                        "title": "Issue with login",
                        "description": "User cannot log in to the system.",
                        "groupCode": "456",
                        "categoryCode": "123",
                        "attachments": ["path-1", "path-2"]
                    },
                    {
                        "pending": True,
                        "title": "Issue with login",
                        "description": "User cannot log in to the system.",
                        "groupCode": "456",
                        "categoryCode": "123",
                        "attachments": []
                    }
                ]
            }
        }


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
    api_log.info("Iniciando API do Chatbot de Suporte Técnico")
    
    # Inicializar base de conhecimento
    rag = KnowledgeBaseRAG()
    api_log.success("Base de conhecimento carregada")
    
    api_log.success("API pronta para receber requisições")


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


@app.post(
    "/chat",
    response_model=MessageResponse,
    summary="Enviar mensagem ao assistente",
    description="Recebe uma mensagem do usuário, processa (suporte ou reserva) e retorna a resposta e tickets criados."
)
async def chat(request: MessageRequest):
    """
    Enviar mensagem para o chatbot
    
    🔥 ATUALIZADO:
    - Usa user_id ao invés de session_id
    - Suporta múltiplos problemas na mesma mensagem
    - Cria um ticket para cada problema
    - Reseta contexto após processar todos os problemas
    
    
    Exemplo de mensagens:
    ```json
    {
      "message": "Quero reservar a sala 202 do segundo andar do prédio de Física. Para o dia 12/02/2026, das 14h às 16h. Para a apresentação de um TCC",
      "user_id": "21012026-t001"
    }

    {
      "message": "Meu computador está lento",
      "user_id": "21012026-t002"
    }

    {
      "message": "Minha CPU pegou fogo e náo liga. Cheirando a queimado e já retirei da tomada",
      "user_id": "21012026-t003"
    }

    {
      "message": "PC lento E impressora travada E email não abre",
      "user_id": "21012026-t003"
    }
    ```
    
    Resultado esperado:
    - 3 problemas identificados
    - 3 tickets criados (um para cada)
    - Contexto resetado após processar todos
    """
    try:
        return await _process_chat(request)
    except Exception as e:
        # Se for erro de tool_use sem tool_result, resetar sessão e tentar uma vez
        err_msg = str(e)
        if "tool_use" in err_msg and "tool_result" in err_msg:
            api_log.warning("Erro de tool_use/tool_result detectado; resetando sessão e tentando novamente")
            user_sessions.pop(request.user_id, None)
            try:
                return await _process_chat(request, is_retry=True)
            except Exception as e2:
                api_log.error(f"Falha após retry: {e2}")
                raise HTTPException(status_code=500, detail=str(e2))
        api_log.error(f"Erro no endpoint /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_chat(request: MessageRequest, is_retry: bool = False):
    """Processa a mensagem via ADK; permite retry controlado."""
    user_id, runner, state, is_new = await get_or_create_user_session(request.userId)
    api_log.info(f"Mensagem recebida | user_id={user_id} | nova_sessao={is_new} | retry={is_retry}")
    api_log.debug(f"Payload: {request.message}")
    
    if state.should_reset_context():
        api_log.warning(f"RESET de contexto para usuário {user_id}")
        state.clear_history_except_current()
    
    full_message = request.message
    attachment_texts = _load_attachments(request.attachments)
    if attachment_texts:
        full_message = f"{request.message}\n\n[ANEXOS]\n" + "\n".join(attachment_texts)
        api_log.info(f"Anexos carregados e adicionados ao contexto ({len(attachment_texts)})")

    state.add_message("user", full_message)
    adk_session = user_sessions[user_id]["adk_session"]
    
    try:
        from google.genai.types import Content, Part
        message_obj = Content(role="user", parts=[Part(text=full_message)])
    except Exception:
        message_obj = {"role": "user", "content": full_message}
    
    from tools import ticket_api_client, set_current_user_id
    set_current_user_id(user_id)
    tickets_before = len(ticket_api_client.local_cache)
    tickets_before_ids = set(ticket_api_client.local_cache.keys())
    
    bot_response = ""
    response_chunks = []
    
    for chunk in runner.run(
        new_message=message_obj,
        session_id=adk_session.id,
        user_id=user_id
    ):
        response_chunks.append(chunk)
        api_log.debug(f"Chunk recebido: {type(chunk)}")
        
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str):
                bot_response = content
            elif hasattr(content, "parts") and content.parts:
                first_part = content.parts[0]
                if hasattr(first_part, "text"):
                    bot_response = first_part.text
                else:
                    bot_response = str(first_part)
            else:
                bot_response = str(content)
        elif hasattr(chunk, "parts"):
            if chunk.parts:
                first_part = chunk.parts[0]
                if hasattr(first_part, "text"):
                    bot_response = first_part.text
                else:
                    bot_response = str(first_part)
        elif hasattr(chunk, "text"):
            bot_response = chunk.text
        elif hasattr(chunk, "message"):
            bot_response = chunk.message
        elif isinstance(chunk, dict):
            bot_response = chunk.get("content") or chunk.get("text") or chunk.get("message") or chunk.get("response", "")
        elif isinstance(chunk, str):
            bot_response = chunk
    
    if not bot_response and response_chunks:
        last_chunk = response_chunks[-1]
        if hasattr(last_chunk, "parts") and getattr(last_chunk, "parts"):
            first_part = last_chunk.parts[0]
            if hasattr(first_part, "text") and first_part.text:
                bot_response = first_part.text
        if not bot_response:
            bot_response = str(last_chunk)
    
    if not bot_response:
        bot_response = "Desculpe, não consegui processar sua mensagem."
        api_log.warning("Resposta vazia do agente; usando fallback")
    
    state.add_message("assistant", bot_response)
    
    tickets_after_ids = set(ticket_api_client.local_cache.keys())
    new_ticket_ids = list(tickets_after_ids - tickets_before_ids)

    tickets_response = []
    for tid in new_ticket_ids:
        ticket = ticket_api_client.local_cache.get(tid, {})
        pending = ticket.get("status", "open") == "open"
        tickets_response.append(
            TicketResponse(
                pending=pending,
                title=ticket.get("description", ""),
                description=ticket.get("description", ""),
                groupCode=ticket.get("group_code", "") or "",
                categoryCode=ticket.get("category_code", "") or "",
                attachments=ticket.get("attachments") or [],
            )
        )
    
    return MessageResponse(
        userId=user_id,
        message=bot_response,
        tickets=tickets_response,
    )


def _load_attachments(paths: Optional[list]) -> list:
    """Carrega anexos do S3 (texto). Retorna lista de strings."""
    if not paths:
        return []
    texts = []
    s3 = boto3.client(
        "s3",
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION,
    )
    for p in paths:
        try:
            bucket, key = _parse_s3_path(p)
            obj = s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
            try:
                text = body.decode("utf-8")
            except Exception:
                text = body[:2048].hex()
            texts.append(f"{p}: {text[:2000]}")
        except (BotoCoreError, ClientError, ValueError) as e:
            api_log.warning(f"Não foi possível carregar anexo {p}: {e}")
            continue
    return texts


def _parse_s3_path(path: str) -> tuple:
    """Converte s3://bucket/key ou bucket/key em (bucket, key)."""
    if path.startswith("s3://"):
        path = path[len("s3://") :]
    if "/" not in path:
        raise ValueError("Formato de caminho inválido para S3. Use s3://bucket/key")
    bucket, key = path.split("/", 1)
    return bucket, key


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
