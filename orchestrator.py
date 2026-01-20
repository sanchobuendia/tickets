"""
Agente Orquestrador - Coordena o fluxo de trabalho entre os agentes especializados
ðŸ”¥ ATUALIZADO: Integrado com session_manager para reset de contexto
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from agents import (
    create_rag_agent,
    create_ticket_creation_agent,
    create_support_agent,
    create_category_classifier_agent,
    create_reservation_agent
)
from logger import agent_logger
from prompts.prompt_orchestrador import orchestrador_instructions
from typing import List, Dict

# ðŸ”¥ NOVO: Importar session_manager
from session_manager import (
    session_manager,
    filter_messages_for_context,
    should_clear_context,
    SessionState
)


def create_orchestrator_agent() -> Agent:
    """
    Agente orquestrador que coordena todo o fluxo de atendimento
    ATUALIZADO: Inclui agente de classificaÃ§Ã£o de categoria
    """
    
    agent_logger.info("ðŸ—ƒï¸ Criando sistema multi-agente...")
    
    agent_logger.info("   â””â”€ Criando agente de suporte tÃ©cnico...")
    support_agent = create_support_agent()
    
    agent_logger.info("   â””â”€ Criando agente de busca na base de conhecimento...")
    rag_agent = create_rag_agent()
    
    agent_logger.info("   â””â”€ Criando agente de classificaÃ§Ã£o de categoria...")
    category_classifier = create_category_classifier_agent()
    
    agent_logger.info("   â””â”€ Criando agente de criaÃ§Ã£o de tickets...")
    ticket_creator = create_ticket_creation_agent()
    
    agent_logger.info("   └─ Criando agente de reservas de salas...")
    reservation_agent = create_reservation_agent()
    
    agent_logger.info("âœ… Todos os agentes criados com sucesso!\n")
    
    orchestrator = Agent(
        name="orchestrator",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=orchestrador_instructions,
        description="Coordena o fluxo de atendimento tÃ©cnico e delega para agentes especializados",
        sub_agents=[
            support_agent, 
            rag_agent, 
            category_classifier,
            ticket_creator,
            reservation_agent,
        ],
    )
    
    return orchestrator


class ConversationState:
    """
    MantÃ©m o estado da conversa para tracking
    ðŸ”¥ ATUALIZADO: Integrado com session_manager
    """
    def __init__(self, user_id: str = "user_123"):
        self.user_id = user_id  # ðŸ”¥ NOVO: ID do usuÃ¡rio
        self.ticket_id = None
        self.problem_resolved = False
        self.user_name = None
        self.issue_description = None
        self.resolution_notes = None
        self.category_code = None
        self.category_group = None
        self.conversation_history = []
        
        agent_logger.debug(f"ðŸ“Š Estado da conversa inicializado para user {user_id}")
    
    def add_message(self, role: str, content: str):
        """Adiciona mensagem ao histÃ³rico"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Log da mensagem
        if role == "user":
            agent_logger.user_message(content)
        elif role == "assistant":
            agent_logger.assistant_message(content)
    
    def get_filtered_history(self) -> List[Dict]:
        """
        ðŸ”¥ NOVO: Retorna histÃ³rico filtrado baseado na sessÃ£o
        
        Se Ãºltima aÃ§Ã£o foi criar ticket, retorna apenas Ãºltima mensagem.
        Caso contrÃ¡rio, retorna histÃ³rico completo.
        """
        if should_clear_context(self.user_id):
            agent_logger.info("ðŸ”„ FILTRO DE CONTEXTO ATIVADO")
            agent_logger.info("   âš ï¸  Ãšltima aÃ§Ã£o: ticket criado")
            agent_logger.info("   ðŸ“Š Retornando apenas mensagem atual (nova sessÃ£o)")
            
            # Retorna apenas Ãºltima mensagem do usuÃ¡rio
            user_messages = [msg for msg in self.conversation_history if msg.get('role') == 'user']
            if user_messages:
                return [user_messages[-1]]
            return []
        else:
            agent_logger.info(f"ðŸ“Š Contexto completo mantido: {len(self.conversation_history)} mensagens")
            return self.conversation_history
    
    def should_reset_context(self) -> bool:
        """
        ðŸ”¥ NOVO: Verifica se deve resetar contexto
        
        IMPORTANTE: SÃ³ retorna TRUE se for uma NOVA mensagem apÃ³s ticket criado.
        NÃ£o retorna TRUE no mesmo turno em que o ticket foi criado.
        """
        from session_manager import should_clear_context
        
        should_reset = should_clear_context(self.user_id)
        
        if should_reset:
            agent_logger.warning("\n" + "="*70)
            agent_logger.warning("ðŸ”„ RESET DE CONTEXTO NECESSÃRIO")
            agent_logger.warning("="*70)
            agent_logger.warning(f"   ðŸ‘¤ User: {self.user_id}")
            agent_logger.warning(f"   ðŸŽ« Ãšltimo ticket: {self.ticket_id}")
            agent_logger.warning(f"   ðŸ“‹ AÃ§Ã£o: Desconsiderar histÃ³rico anterior")
            agent_logger.warning("="*70 + "\n")
        
        return should_reset
    
    def _has_pending_reset(self) -> bool:
        """Verifica se hÃ¡ reset pendente sem disparar logs"""
        from session_manager import should_clear_context
        return should_clear_context(self.user_id)
    
    def check_session_state(self) -> str:
        """
        ðŸ”¥ NOVO: Retorna estado atual da sessÃ£o
        """
        session = session_manager.get_or_create_session(self.user_id)
        return session.state.value
    
    def set_ticket_id(self, ticket_id: str):
        """Define o ID do ticket"""
        self.ticket_id = ticket_id
        agent_logger.info(f"ðŸŽ« Ticket ID definido: {ticket_id}")
    
    def set_category_code(self, code: str, group: str = None):
        """Define o cÃ³digo de categoria"""
        self.category_code = code
        self.category_group = group
        agent_logger.info(f"ðŸ”¢ CÃ³digo de categoria definido: {code} ({group})")
    
    def set_problem_resolved(self, resolved: bool):
        """Marca o problema como resolvido ou nÃ£o"""
        self.problem_resolved = resolved
        status = "âœ… RESOLVIDO" if resolved else "â³ EM ANDAMENTO"
        agent_logger.info(f"ðŸ“Œ Status do problema: {status}")
        
        # ðŸ”¥ NOVO: Atualizar estado da sessÃ£o
        if resolved:
            session_manager.update_session_state(self.user_id, SessionState.WAITING_CONFIRMATION)
    
    def set_user_name(self, name: str):
        """Define o nome do usuÃ¡rio"""
        self.user_name = name
        agent_logger.info(f"ðŸ‘¤ UsuÃ¡rio identificado: {name}")
    
    def set_issue_description(self, description: str):
        """Define a descriÃ§Ã£o do problema"""
        self.issue_description = description
        agent_logger.info(f"ðŸ“ Problema registrado: {description[:80]}...")
        
        # ðŸ”¥ NOVO: Iniciar nova sessÃ£o
        session_manager.start_new_session(self.user_id, description)
    
    def set_resolution_notes(self, notes: str):
        """Define as notas de resoluÃ§Ã£o"""
        self.resolution_notes = notes
        agent_logger.info(f"âœ… ResoluÃ§Ã£o documentada: {notes[:80]}...")
    
    def clear_history_except_current(self):
        """
        ðŸ”¥ NOVO: Limpa histÃ³rico mantendo apenas a Ãºltima mensagem
        """
        if self.conversation_history:
            last_message = self.conversation_history[-1]
            self.conversation_history = [last_message]
            
            agent_logger.info("\n" + "="*70)
            agent_logger.info("ðŸ§¹ LIMPEZA DE HISTÃ“RICO")
            agent_logger.info("="*70)
            agent_logger.info(f"   ðŸ“Š HistÃ³rico anterior: DESCARTADO")
            agent_logger.info(f"   ðŸ“¨ Mantido: Apenas Ãºltima mensagem")
            agent_logger.info("="*70 + "\n")
    
    def get_summary(self) -> dict:
        """Retorna resumo do estado atual"""
        summary = {
            "user_id": self.user_id,  # ðŸ”¥ NOVO
            "session_state": self.check_session_state(),  # ðŸ”¥ NOVO
            "ticket_id": self.ticket_id,
            "category_code": self.category_code,
            "category_group": self.category_group,
            "problem_resolved": self.problem_resolved,
            "user_name": self.user_name,
            "issue_description": self.issue_description,
            "resolution_notes": self.resolution_notes,
            "messages_count": len(self.conversation_history),
            "should_reset": self.should_reset_context()  # ðŸ”¥ NOVO
        }
        
        agent_logger.debug(f"ðŸ“Š Resumo do estado: {summary}")
        
        return summary