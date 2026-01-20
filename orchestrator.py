"""
Agente Orquestrador - Coordena o fluxo de trabalho entre os agentes especializados
ATUALIZADO: Inclui agente de classificação de categoria
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from agents import (
    create_rag_agent,
    create_ticket_creation_agent,
    create_support_agent,
    create_category_classifier_agent
)
from logger import agent_logger
from prompts.prompt_orchestrador import orchestrador_instructions


def create_orchestrator_agent() -> Agent:
    """
    Agente orquestrador que coordena todo o fluxo de atendimento
    ATUALIZADO: Inclui agente de classificação de categoria
    """
    
    agent_logger.info("🏗️  Criando sistema multi-agente...")
    
    agent_logger.info("   └─ Criando agente de suporte técnico...")
    support_agent = create_support_agent()
    
    agent_logger.info("   └─ Criando agente de busca na base de conhecimento...")
    rag_agent = create_rag_agent()
    
    agent_logger.info("   └─ Criando agente de classificação de categoria...")
    category_classifier = create_category_classifier_agent()  # NOVO
    
    agent_logger.info("   └─ Criando agente de criação de tickets...")
    ticket_creator = create_ticket_creation_agent()
    
    agent_logger.info("✅ Todos os agentes criados com sucesso!\n")
    
    orchestrator = Agent(
        name="orchestrator",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=orchestrador_instructions,
        description="Coordena o fluxo de atendimento técnico e delega para agentes especializados",
        sub_agents=[
            support_agent, 
            rag_agent, 
            category_classifier,  # NOVO
            ticket_creator
        ],
    )
    
    return orchestrator


class ConversationState:
    """
    Mantém o estado da conversa para tracking
    COM LOGGING DE MUDANÇAS DE ESTADO
    ATUALIZADO: Inclui código de categoria
    """
    def __init__(self):
        self.ticket_id = None
        self.problem_resolved = False
        self.user_name = None
        self.issue_description = None
        self.resolution_notes = None
        self.category_code = None  # NOVO
        self.category_group = None  # NOVO
        self.conversation_history = []
        
        agent_logger.debug("📊 Estado da conversa inicializado")
    
    def add_message(self, role: str, content: str):
        """Adiciona mensagem ao histórico"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Log da mensagem
        if role == "user":
            agent_logger.user_message(content)
        elif role == "assistant":
            agent_logger.assistant_message(content)
    
    def set_ticket_id(self, ticket_id: str):
        """Define o ID do ticket"""
        self.ticket_id = ticket_id
        agent_logger.info(f"🎫 Ticket ID definido: {ticket_id}")
    
    def set_category_code(self, code: str, group: str = None):
        """Define o código de categoria - NOVO"""
        self.category_code = code
        self.category_group = group
        agent_logger.info(f"🔢 Código de categoria definido: {code} ({group})")
    
    def set_problem_resolved(self, resolved: bool):
        """Marca o problema como resolvido ou não"""
        self.problem_resolved = resolved
        status = "✅ RESOLVIDO" if resolved else "⏳ EM ANDAMENTO"
        agent_logger.info(f"📌 Status do problema: {status}")
    
    def set_user_name(self, name: str):
        """Define o nome do usuário"""
        self.user_name = name
        agent_logger.info(f"👤 Usuário identificado: {name}")
    
    def set_issue_description(self, description: str):
        """Define a descrição do problema"""
        self.issue_description = description
        agent_logger.info(f"📝 Problema registrado: {description[:80]}...")
    
    def set_resolution_notes(self, notes: str):
        """Define as notas de resolução"""
        self.resolution_notes = notes
        agent_logger.info(f"✅ Resolução documentada: {notes[:80]}...")
    
    def get_summary(self) -> dict:
        """Retorna resumo do estado atual"""
        summary = {
            "ticket_id": self.ticket_id,
            "category_code": self.category_code,  # NOVO
            "category_group": self.category_group,  # NOVO
            "problem_resolved": self.problem_resolved,
            "user_name": self.user_name,
            "issue_description": self.issue_description,
            "resolution_notes": self.resolution_notes,
            "messages_count": len(self.conversation_history)
        }
        
        agent_logger.debug(f"📊 Resumo do estado: {summary}")
        
        return summary