"""
Tools para gerenciamento de tickets (apenas em cache local).
Removido call externo; agora apenas organiza dados e armazena em memória.
"""
from typing import Dict, Any, Optional, List
from config import Config
from logger import agent_logger
import uuid
from datetime import datetime
import litellm

# Desabilitar logging assíncrono do LiteLLM
litellm.turn_off_message_logging = True
litellm.suppress_debug_info = True
litellm.drop_params = True

# 🔥 Variável global para armazenar user_id atual
_current_user_id = None


def set_current_user_id(user_id: str):
    """Define o user_id atual para a thread"""
    global _current_user_id
    _current_user_id = user_id
    agent_logger.info(f"🔧 user_id definido no contexto: {user_id}")


def _get_user_id_from_context() -> Optional[str]:
    """Obtém user_id do contexto atual"""
    global _current_user_id
    if _current_user_id:
        agent_logger.info(f"✅ user_id obtido do contexto: {_current_user_id}")
    else:
        agent_logger.warning("⚠️ user_id não encontrado no contexto - usando default")
        _current_user_id = "user_default"
    return _current_user_id


class TicketAPIClient:
    """Cliente de Tickets apenas em memória."""

    def __init__(self):
        agent_logger.info("🌐 Cliente de Tickets (cache local) inicializado")
        self.local_cache: Dict[str, Dict[str, Any]] = {}

    def create_ticket(
        self,
        user_name: str,
        issue_description: str,
        priority: str,
        status: str = "open",
        resolution: Optional[str] = None,
        category_code: Optional[str] = None,
        group_code: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Cria um ticket apenas no cache local."""
        local_ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"

        if not category_code:
            category_code = kwargs.get("codigo")
        if not group_code:
            group_code = kwargs.get("grupo")

        ticket = {
            "id": local_ticket_id,
            "user_name": user_name,
            "description": issue_description,
            "priority": priority,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "category_code": category_code or "",
            "group_code": group_code or "",
            "attachments": attachments or [],
        }

        if status == "closed":
            if not resolution:
                resolution = "Problema resolvido pelo agente de suporte"
            ticket["resolution_notes"] = resolution
            ticket["closed_at"] = datetime.now().isoformat()

        desc_preview = (issue_description[:77] + "...") if len(issue_description) > 80 else issue_description
        summary = f"Ticket {local_ticket_id} [{status}] | Prioridade: {priority} | {desc_preview}"
        if resolution:
            summary += f" | Resolução: {resolution[:60] + '...' if len(resolution) > 60 else resolution}"
        ticket["summary"] = summary

        self.local_cache[local_ticket_id] = ticket

        log_msg = "TICKET CRIADO JÁ FECHADO" if status == "closed" else "TICKET CRIADO (ABERTO)"
        agent_logger.info("\n   " + "─" * 50)
        agent_logger.info(f"   {log_msg}")
        agent_logger.info(f"   🎫 ID: {local_ticket_id}")
        agent_logger.info(f"   👤 Usuário: {user_name}")
        agent_logger.info(f"   📋 Description: {issue_description}")
        agent_logger.info(f"   ⚡ Prioridade: {priority}")
        if category_code:
            agent_logger.info(f"   🔢 Categoria: {category_code}")
        if group_code:
            agent_logger.info(f"   🗂️  Grupo: {group_code}")
        if status == "closed" and resolution:
            agent_logger.info(
                f"   📝 Resolução: {resolution[:50]}..." if len(resolution) > 50 else f"   📝 Resolução: {resolution}"
            )
        agent_logger.info("   " + "─" * 50 + "\n")

        message = f"🎫 {summary}"

        return {
            "success": True,
            "ticket_id": local_ticket_id,
            "status": status,
            "summary": summary,
            "message": message,
            "priority": priority,
            "description": issue_description,
            "resolution": resolution,
            "category_code": category_code or "",
            "group_code": group_code or "",
            "attachments": attachments or [],
        }

    def close_ticket(self, ticket_id: str, resolution_notes: str) -> Dict[str, Any]:
        """Fecha um ticket no cache local."""
        ticket = self.local_cache.get(ticket_id)
        if not ticket:
            return {"success": False, "message": "Ticket não encontrado"}

        ticket["status"] = "closed"
        ticket["resolution_notes"] = resolution_notes
        ticket["closed_at"] = datetime.now().isoformat()
        self.local_cache[ticket_id] = ticket

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": "closed",
            "resolution": resolution_notes,
        }

    def get_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """Consulta status no cache."""
        ticket = self.local_cache.get(ticket_id)
        if not ticket:
            return {"success": False, "message": "Ticket não encontrado"}
        return {"success": True, "status": ticket.get("status", ""), "ticket": ticket}


# Instância global do cliente de API
ticket_api_client = TicketAPIClient()


def create_ticket(
    user_name: str,
    issue_description: str,
    priority: str = "medium",
    status: str = "open",
    resolution: Optional[str] = None,
    category_code: Optional[str] = None,
    group_code: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Cria um novo ticket no cache local.
    Também marca sessão como completa via session_manager.
    """
    from session_manager import mark_attendance_completed

    user_id = _get_user_id_from_context()

    agent_logger.tool_call(
        "ticket_api",
        "create_ticket",
        {
            "user_name": user_name,
            "priority": priority,
            "status": status,
            "description": issue_description[:50] + "...",
            "user_id": user_id,
        },
    )

    try:
        result = ticket_api_client.create_ticket(
            user_name,
            issue_description,
            priority,
            status,
            resolution,
            category_code,
            group_code,
            attachments,
            **kwargs,
        )

        if result["success"]:
            ticket_id = result["ticket_id"]

            if user_id:
                agent_logger.info("\n" + "=" * 70)
                agent_logger.info(f"🔄 MARCANDO SESSÃO COMO COMPLETA")
                agent_logger.info(f"   👤 User ID: {user_id}")
                agent_logger.info(f"   🎫 Ticket ID: {ticket_id}")

                mark_attendance_completed(user_id, ticket_id)

                agent_logger.success(f"✅ SESSÃO COMPLETA - Próxima mensagem = NOVO atendimento")
                agent_logger.info(f"   📊 Histórico será desconsiderado na próxima interação")
                agent_logger.info("=" * 70 + "\n")
            else:
                agent_logger.warning("\n⚠️  ATENÇÃO: user_id não fornecido")
                agent_logger.warning("   Sessão NÃO será marcada como completa")
                agent_logger.warning("   Histórico NÃO será resetado\n")

            agent_logger.tool_result("create_ticket", True, f"Ticket {ticket_id} criado (cache local)")
        else:
            agent_logger.tool_result("create_ticket", False, result["message"])

        return result

    except Exception as e:
        error_msg = f"Erro ao criar ticket: {str(e)}"
        agent_logger.tool_result("create_ticket", False, error_msg)
        return {
            "success": False,
            "message": error_msg,
        }


def close_ticket(
    ticket_id: str,
    resolution_notes: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fecha um ticket no cache local."""
    from session_manager import mark_attendance_completed

    agent_logger.tool_call(
        "ticket_api",
        "close_ticket",
        {
            "ticket_id": ticket_id,
            "resolution": resolution_notes[:50] + "...",
            "user_id": user_id,
        },
    )

    try:
        result = ticket_api_client.close_ticket(ticket_id, resolution_notes)

        if result["success"]:
            if user_id:
                agent_logger.info(f"🔄 Marcando sessão como completa para user {user_id}")
                mark_attendance_completed(user_id, ticket_id)
                agent_logger.success(f"✅ Sessão marcada - próxima msg = NOVO atendimento")

            agent_logger.tool_result("close_ticket", True, f"Ticket {ticket_id} fechado (cache local)")
        else:
            agent_logger.tool_result("close_ticket", False, result["message"])

        return result

    except Exception as e:
        error_msg = f"Erro ao fechar ticket: {str(e)}"
        agent_logger.tool_result("close_ticket", False, error_msg)
        return {
            "success": False,
            "message": error_msg,
        }


def get_ticket_status(ticket_id: str) -> Dict[str, Any]:
    """Consulta o status de um ticket no cache local."""
    agent_logger.tool_call("ticket_api", "get_ticket_status", {"ticket_id": ticket_id})

    try:
        result = ticket_api_client.get_ticket_status(ticket_id)

        if result["success"]:
            agent_logger.tool_result("get_ticket_status", True, f"Status: {result['status']}")
        else:
            agent_logger.tool_result("get_ticket_status", False, result["message"])

        return result

    except Exception as e:
        error_msg = f"Erro ao consultar ticket: {str(e)}"
        agent_logger.tool_result("get_ticket_status", False, error_msg)
        return {
            "success": False,
            "message": error_msg,
        }


def list_all_tickets() -> Dict[str, Any]:
    """Lista todos os tickets do sistema (cache local)"""
    agent_logger.info("📋 Listando todos os tickets do cache local...")

    tickets = ticket_api_client.local_cache
    open_tickets = [t for t in tickets.values() if t.get("status") == "open"]
    closed_tickets = [t for t in tickets.values() if t.get("status") == "closed"]

    agent_logger.info(f"   🟢 Tickets abertos: {len(open_tickets)}")
    agent_logger.info(f"   🔴 Tickets fechados: {len(closed_tickets)}")

    return {
        "total": len(tickets),
        "open": len(open_tickets),
        "closed": len(closed_tickets),
        "tickets": tickets,
    }
