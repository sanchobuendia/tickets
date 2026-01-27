"""
Gerenciador de SessÃ£o de Atendimento
Controla o ciclo de vida de cada problema tÃ©cnico e permite reset contextual
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class SessionState(Enum):
    """Estados possÃ­veis de uma sessÃ£o de atendimento"""
    IDLE = "idle"  # Aguardando novo problema
    NEW_SESSION = "new_session"  # 🔥 NOVO: Primeira mensagem após ticket criado
    DIAGNOSING = "diagnosing"  # Diagnosticando problema
    RESOLVING = "resolving"  # Tentando resolver
    WAITING_CONFIRMATION = "waiting_confirmation"  # Aguardando "resolveu?"
    TICKET_CREATING = "ticket_creating"  # Criando ticket
    COMPLETED = "completed"  # Atendimento finalizado


class AttendanceSession:
    """Representa uma sessÃ£o de atendimento para um problema especÃ­fico"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = SessionState.IDLE
        self.problem_description: Optional[str] = None
        self.category_code: Optional[str] = None
        self.ticket_id: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.message_count = 0
        
    def start_new_problem(self, problem: str, is_new_session: bool = False):
        """
        Inicia novo problema
        
        Args:
            problem: Descrição do problema
            is_new_session: True se é primeiro problema após ticket criado
        """
        if is_new_session:
            self.state = SessionState.NEW_SESSION
        else:
            self.state = SessionState.DIAGNOSING
        
        self.problem_description = problem
        self.message_count = 0
        
    def mark_completed(self, ticket_id: str):
        """Marca atendimento como completo"""
        self.state = SessionState.COMPLETED
        self.ticket_id = ticket_id
        self.completed_at = datetime.now()
        
    def is_completed(self) -> bool:
        """Verifica se sessÃ£o estÃ¡ completa"""
        return self.state == SessionState.COMPLETED
    
    def is_new_session(self) -> bool:
        """🔥 NOVO: Verifica se é uma nova sessão (primeiro problema após ticket)"""
        return self.state == SessionState.NEW_SESSION
    
    def reset(self):
        """Reseta sessÃ£o para novo atendimento"""
        self.state = SessionState.IDLE
        self.problem_description = None
        self.category_code = None
        self.ticket_id = None
        self.completed_at = None
        self.message_count = 0


class SessionManager:
    """
    Gerenciador central de sessÃµes
    MantÃ©m controle de atendimentos por usuÃ¡rio
    """
    
    def __init__(self):
        self.sessions: Dict[str, AttendanceSession] = {}
        
    def get_or_create_session(self, user_id: str) -> AttendanceSession:
        """ObtÃ©m sessÃ£o existente ou cria nova"""
        if user_id not in self.sessions:
            self.sessions[user_id] = AttendanceSession(user_id)
        return self.sessions[user_id]
    
    def should_reset_context(self, user_id: str) -> bool:
        """
        Verifica se deve resetar contexto para este usuÃ¡rio
        Retorna True se Ãºltimo atendimento foi completado
        """
        if user_id not in self.sessions:
            return False
            
        session = self.sessions[user_id]
        return session.is_completed()
    
    def get_relevant_messages(self, user_id: str, all_messages: List[Dict]) -> List[Dict]:
        """
        Filtra mensagens relevantes para o atendimento atual
        Remove mensagens de atendimentos anteriores jÃ¡ finalizados
        """
        session = self.get_or_create_session(user_id)
        
        # Se sessÃ£o foi completada, retorna apenas a Ãºltima mensagem (nova solicitaÃ§Ã£o)
        if session.is_completed():
            # Pega apenas a Ãºltima mensagem do usuÃ¡rio
            user_messages = [msg for msg in all_messages if msg.get('role') == 'user']
            return user_messages[-1:] if user_messages else []
        
        # Se sessÃ£o estÃ¡ ativa, retorna todas as mensagens da sessÃ£o atual
        if session.created_at:
            # Filtra mensagens apÃ³s inÃ­cio da sessÃ£o
            return [
                msg for msg in all_messages 
                if self._message_is_after_session_start(msg, session.created_at)
            ]
        
        return all_messages
    
    def mark_session_completed(self, user_id: str, ticket_id: str):
        """Marca sessÃ£o como completa apÃ³s criar ticket"""
        session = self.get_or_create_session(user_id)
        session.mark_completed(ticket_id)
    
    def start_new_session(self, user_id: str, problem: str):
        """
        Inicia nova sessÃ£o de atendimento
        🔥 ATUALIZADO: Detecta se é novo atendimento após ticket
        """
        session = self.get_or_create_session(user_id)
        
        # 🔥 NOVO: Verificar se é nova sessão (após ticket criado)
        is_new_session = session.is_completed()
        
        # Se jÃ¡ tinha sessÃ£o completa, reseta
        if is_new_session:
            session.reset()
        
        # Iniciar com flag de nova sessão se aplicável
        session.start_new_problem(problem, is_new_session=is_new_session)
    
    def update_session_state(self, user_id: str, new_state: SessionState):
        """Atualiza estado da sessÃ£o"""
        session = self.get_or_create_session(user_id)
        session.state = new_state
    
    def set_category_code(self, user_id: str, code: str):
        """Armazena cÃ³digo de categoria"""
        session = self.get_or_create_session(user_id)
        session.category_code = code
    
    @staticmethod
    def _message_is_after_session_start(message: Dict, session_start: datetime) -> bool:
        """Verifica se mensagem Ã© posterior ao inÃ­cio da sessÃ£o"""
        # Assume que mensagens tÃªm timestamp
        msg_timestamp = message.get('timestamp')
        if msg_timestamp:
            if isinstance(msg_timestamp, str):
                msg_timestamp = datetime.fromisoformat(msg_timestamp)
            return msg_timestamp >= session_start
        return True  # Se nÃ£o tem timestamp, considera relevante


# InstÃ¢ncia singleton para uso global
session_manager = SessionManager()


def filter_messages_for_context(user_id: str, messages: List[Dict]) -> List[Dict]:
    """
    FunÃ§Ã£o helper para filtrar mensagens antes de passar para LLM
    
    Args:
        user_id: ID do usuÃ¡rio (nÃºmero WhatsApp, por exemplo)
        messages: Lista completa de mensagens da conversa
        
    Returns:
        Lista filtrada de mensagens relevantes para o contexto atual
    """
    return session_manager.get_relevant_messages(user_id, messages)


def mark_attendance_completed(user_id: str, ticket_id: str):
    """
    FunÃ§Ã£o helper para marcar atendimento como completo
    Deve ser chamada APÃ“S criar o ticket
    
    Args:
        user_id: ID do usuÃ¡rio
        ticket_id: ID do ticket criado (ex: "TKT-A1B2")
    """
    session_manager.mark_session_completed(user_id, ticket_id)


def should_clear_context(user_id: str) -> bool:
    """
    Verifica se deve limpar contexto para prÃ³xima mensagem
    
    Args:
        user_id: ID do usuÃ¡rio
        
    Returns:
        True se Ãºltimo atendimento foi completado
    """
    return session_manager.should_reset_context(user_id)


def is_new_session_starting(user_id: str) -> bool:
    """
    🔥 NOVO: Verifica se é o INÍCIO de uma nova sessão
    (primeira mensagem após ticket criado)
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se está iniciando nova sessão (deve executar fluxo completo)
    """
    session = session_manager.get_or_create_session(user_id)
    return session.is_new_session()