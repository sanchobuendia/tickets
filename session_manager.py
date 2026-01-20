"""
Gerenciador de Sessão de Atendimento
Controla o ciclo de vida de cada problema técnico e permite reset contextual
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class SessionState(Enum):
    """Estados possíveis de uma sessão de atendimento"""
    IDLE = "idle"  # Aguardando novo problema
    DIAGNOSING = "diagnosing"  # Diagnosticando problema
    RESOLVING = "resolving"  # Tentando resolver
    WAITING_CONFIRMATION = "waiting_confirmation"  # Aguardando "resolveu?"
    TICKET_CREATING = "ticket_creating"  # Criando ticket
    COMPLETED = "completed"  # Atendimento finalizado


class AttendanceSession:
    """Representa uma sessão de atendimento para um problema específico"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = SessionState.IDLE
        self.problem_description: Optional[str] = None
        self.category_code: Optional[str] = None
        self.ticket_id: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.message_count = 0
        
    def start_new_problem(self, problem: str):
        """Inicia novo problema"""
        self.state = SessionState.DIAGNOSING
        self.problem_description = problem
        self.message_count = 0
        
    def mark_completed(self, ticket_id: str):
        """Marca atendimento como completo"""
        self.state = SessionState.COMPLETED
        self.ticket_id = ticket_id
        self.completed_at = datetime.now()
        
    def is_completed(self) -> bool:
        """Verifica se sessão está completa"""
        return self.state == SessionState.COMPLETED
    
    def reset(self):
        """Reseta sessão para novo atendimento"""
        self.state = SessionState.IDLE
        self.problem_description = None
        self.category_code = None
        self.ticket_id = None
        self.completed_at = None
        self.message_count = 0


class SessionManager:
    """
    Gerenciador central de sessões
    Mantém controle de atendimentos por usuário
    """
    
    def __init__(self):
        self.sessions: Dict[str, AttendanceSession] = {}
        
    def get_or_create_session(self, user_id: str) -> AttendanceSession:
        """Obtém sessão existente ou cria nova"""
        if user_id not in self.sessions:
            self.sessions[user_id] = AttendanceSession(user_id)
        return self.sessions[user_id]
    
    def should_reset_context(self, user_id: str) -> bool:
        """
        Verifica se deve resetar contexto para este usuário
        Retorna True se último atendimento foi completado
        """
        if user_id not in self.sessions:
            return False
            
        session = self.sessions[user_id]
        return session.is_completed()
    
    def get_relevant_messages(self, user_id: str, all_messages: List[Dict]) -> List[Dict]:
        """
        Filtra mensagens relevantes para o atendimento atual
        Remove mensagens de atendimentos anteriores já finalizados
        """
        session = self.get_or_create_session(user_id)
        
        # Se sessão foi completada, retorna apenas a última mensagem (nova solicitação)
        if session.is_completed():
            # Pega apenas a última mensagem do usuário
            user_messages = [msg for msg in all_messages if msg.get('role') == 'user']
            return user_messages[-1:] if user_messages else []
        
        # Se sessão está ativa, retorna todas as mensagens da sessão atual
        if session.created_at:
            # Filtra mensagens após início da sessão
            return [
                msg for msg in all_messages 
                if self._message_is_after_session_start(msg, session.created_at)
            ]
        
        return all_messages
    
    def mark_session_completed(self, user_id: str, ticket_id: str):
        """Marca sessão como completa após criar ticket"""
        session = self.get_or_create_session(user_id)
        session.mark_completed(ticket_id)
    
    def start_new_session(self, user_id: str, problem: str):
        """Inicia nova sessão de atendimento"""
        session = self.get_or_create_session(user_id)
        
        # Se já tinha sessão completa, reseta
        if session.is_completed():
            session.reset()
        
        session.start_new_problem(problem)
    
    def update_session_state(self, user_id: str, new_state: SessionState):
        """Atualiza estado da sessão"""
        session = self.get_or_create_session(user_id)
        session.state = new_state
    
    def set_category_code(self, user_id: str, code: str):
        """Armazena código de categoria"""
        session = self.get_or_create_session(user_id)
        session.category_code = code
    
    @staticmethod
    def _message_is_after_session_start(message: Dict, session_start: datetime) -> bool:
        """Verifica se mensagem é posterior ao início da sessão"""
        # Assume que mensagens têm timestamp
        msg_timestamp = message.get('timestamp')
        if msg_timestamp:
            if isinstance(msg_timestamp, str):
                msg_timestamp = datetime.fromisoformat(msg_timestamp)
            return msg_timestamp >= session_start
        return True  # Se não tem timestamp, considera relevante


# Instância singleton para uso global
session_manager = SessionManager()


def filter_messages_for_context(user_id: str, messages: List[Dict]) -> List[Dict]:
    """
    Função helper para filtrar mensagens antes de passar para LLM
    
    Args:
        user_id: ID do usuário (número WhatsApp, por exemplo)
        messages: Lista completa de mensagens da conversa
        
    Returns:
        Lista filtrada de mensagens relevantes para o contexto atual
    """
    return session_manager.get_relevant_messages(user_id, messages)


def mark_attendance_completed(user_id: str, ticket_id: str):
    """
    Função helper para marcar atendimento como completo
    Deve ser chamada APÓS criar o ticket
    
    Args:
        user_id: ID do usuário
        ticket_id: ID do ticket criado (ex: "TKT-A1B2")
    """
    session_manager.mark_session_completed(user_id, ticket_id)


def should_clear_context(user_id: str) -> bool:
    """
    Verifica se deve limpar contexto para próxima mensagem
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se último atendimento foi completado
    """
    return session_manager.should_reset_context(user_id)