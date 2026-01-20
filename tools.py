"""
Tools para gerenciamento de tickets via API PÚBLICA
USA JSONPlaceholder (https://jsonplaceholder.typicode.com/) como POC
ATUALIZADO: Integrado com session_manager para reset de contexto
"""
import requests
import json
from typing import Dict, Any, Optional
from config import Config
from logger import agent_logger
import uuid
from datetime import datetime
import litellm

# Desabilitar logging assíncrono do LiteLLM
litellm.turn_off_message_logging = True
litellm.suppress_debug_info = True
litellm.drop_params = True


# 🔥 NOVO: Variável global para armazenar user_id atual
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
    """Cliente para API de Tickets usando JSONPlaceholder"""
    
    BASE_URL = "https://jsonplaceholder.typicode.com"
    
    def __init__(self):
        agent_logger.info("🌐 Cliente de API de Tickets Inicializado")
        agent_logger.info(f"   Base URL: {self.BASE_URL}")
        self.local_cache = {}
    
    def create_ticket(
        self, 
        user_name: str, 
        issue_description: str, 
        priority: str,
        status: str = "open",
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria um ticket via API REST com status configurável"""
        agent_logger.info("📄 Fazendo requisição HTTP para criar ticket...")
        
        local_ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        
        payload = {
            "title": f"Suporte Técnico - {user_name}",
            "body": issue_description,
            "userId": 1,
            "priority": priority,
            "status": status,
            "localId": local_ticket_id
        }
        
        if status == "closed":
            if not resolution:
                resolution = "Problema resolvido pelo agente de suporte"
            payload["resolution"] = resolution
            payload["closedAt"] = datetime.now().isoformat()
        
        agent_logger.info(f"   📤 POST {self.BASE_URL}/posts")
        agent_logger.debug(f"   📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/posts",
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            agent_logger.info(f"   📥 Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                agent_logger.info(f"   ✅ Resposta recebida: ID={data.get('id')}")
                
                remote_id = data.get("id")
                
                ticket = {
                    "id": local_ticket_id,
                    "remote_id": remote_id,
                    "user_name": user_name,
                    "description": issue_description,
                    "priority": priority,
                    "status": status,
                    "created_at": datetime.now().isoformat(),
                    "api_response": data
                }
                
                if resolution:
                    ticket["resolution_notes"] = resolution
                    ticket["closed_at"] = datetime.now().isoformat()
                
                self.local_cache[local_ticket_id] = ticket
                
                agent_logger.info(f"   💾 Ticket armazenado em cache local")
                
                if status == "closed":
                    agent_logger.info("\n   " + "─"*50)
                    agent_logger.info(f"   ✅ TICKET CRIADO JÁ FECHADO")
                    agent_logger.info(f"   🎫 ID: {local_ticket_id}")
                    agent_logger.info(f"   👤 Usuário: {user_name}")
                    agent_logger.info(f"   📋 Description: {issue_description}")
                    agent_logger.info(f"   ⚡ Prioridade: {priority}")
                    agent_logger.info(f"   📝 Resolução: {resolution[:50]}..." if resolution and len(resolution) > 50 else f"   📝 Resolução: {resolution}")
                    agent_logger.info("   " + "─"*50 + "\n")
                    message = f"✅ Ticket #{local_ticket_id} criado e fechado via API"
                else:
                    agent_logger.info("\n   " + "─"*50)
                    agent_logger.info(f"   📋 TICKET CRIADO (ABERTO)")
                    agent_logger.info(f"   🎫 ID: {local_ticket_id}")
                    agent_logger.info(f"   👤 Usuário: {user_name}")
                    agent_logger.info(f"   📋 Description: {issue_description}")
                    agent_logger.info(f"   ⚡ Prioridade: {priority}")
                    agent_logger.info(f"   ⏳ Status: ABERTO - Aguardando técnico")
                    agent_logger.info("   " + "─"*50 + "\n")
                    message = f"✅ Ticket #{local_ticket_id} criado com sucesso via API"
                
                return {
                    "success": True,
                    "ticket_id": local_ticket_id,
                    "remote_id": remote_id,
                    "status": status,
                    "message": message,
                    "priority": priority,
                    "description": issue_description,
                    "resolution": resolution,
                    "api_response": data
                }
            else:
                agent_logger.error(f"   ❌ Erro HTTP: {response.status_code}")
                agent_logger.debug(f"   Resposta: {response.text}")
                return {
                    "success": False,
                    "message": f"Erro ao criar ticket: HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            agent_logger.error("   ⏱️ Timeout na requisição")
            return {
                "success": False,
                "message": "Timeout ao criar ticket na API"
            }
        except requests.exceptions.RequestException as e:
            agent_logger.error(f"   ❌ Erro de rede: {str(e)}")
            return {
                "success": False,
                "message": f"Erro de conexão: {str(e)}"
            }
    
    def close_ticket(self, ticket_id: str, resolution_notes: str) -> Dict[str, Any]:
        """Fecha um ticket via API REST"""
        agent_logger.info(f"📄 Fazendo requisição HTTP para fechar ticket {ticket_id}...")
        
        ticket = self.local_cache.get(ticket_id)
        
        if not ticket:
            agent_logger.warning(f"   ⚠️ Ticket {ticket_id} não encontrado no cache local")
            remote_id = 1
        else:
            remote_id = ticket.get("remote_id", 1)
        
        payload = {
            "id": remote_id,
            "status": "closed",
            "resolution": resolution_notes,
            "closedAt": datetime.now().isoformat()
        }
        
        agent_logger.info(f"   📤 PUT {self.BASE_URL}/posts/{remote_id}")
        agent_logger.debug(f"   📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.put(
                f"{self.BASE_URL}/posts/{remote_id}",
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            agent_logger.info(f"   📥 Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                agent_logger.info(f"   ✅ Ticket fechado na API")
                
                if ticket:
                    ticket["status"] = "closed"
                    ticket["resolution_notes"] = resolution_notes
                    ticket["closed_at"] = datetime.now().isoformat()
                    self.local_cache[ticket_id] = ticket
                
                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "remote_id": remote_id,
                    "status": "closed",
                    "message": f"✅ Ticket #{ticket_id} fechado com sucesso via API",
                    "resolution": resolution_notes,
                    "api_response": data
                }
            else:
                agent_logger.error(f"   ❌ Erro HTTP: {response.status_code}")
                return {
                    "success": False,
                    "message": f"Erro ao fechar ticket: HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            agent_logger.error("   ⏱️ Timeout na requisição")
            return {
                "success": False,
                "message": "Timeout ao fechar ticket na API"
            }
        except requests.exceptions.RequestException as e:
            agent_logger.error(f"   ❌ Erro de rede: {str(e)}")
            return {
                "success": False,
                "message": f"Erro de conexão: {str(e)}"
            }
    
    def get_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """Consulta o status de um ticket via API REST"""
        agent_logger.info(f"📄 Consultando ticket {ticket_id} na API...")
        
        ticket = self.local_cache.get(ticket_id)
        
        if not ticket:
            agent_logger.warning(f"   ⚠️ Ticket {ticket_id} não encontrado no cache local")
            return {
                "success": False,
                "message": f"Ticket {ticket_id} não encontrado"
            }
        
        remote_id = ticket.get("remote_id", 1)
        
        agent_logger.info(f"   📤 GET {self.BASE_URL}/posts/{remote_id}")
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/posts/{remote_id}",
                timeout=10
            )
            
            agent_logger.info(f"   📥 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                agent_logger.info(f"   ✅ Dados do ticket recuperados")
                
                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "remote_id": remote_id,
                    "status": ticket.get("status", "open"),
                    "user_name": ticket.get("user_name"),
                    "description": ticket.get("description"),
                    "priority": ticket.get("priority"),
                    "created_at": ticket.get("created_at"),
                    "resolution_notes": ticket.get("resolution_notes"),
                    "api_response": data
                }
            else:
                agent_logger.error(f"   ❌ Erro HTTP: {response.status_code}")
                return {
                    "success": False,
                    "message": f"Erro ao consultar ticket: HTTP {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            agent_logger.error(f"   ❌ Erro de rede: {str(e)}")
            return {
                "success": False,
                "message": f"Erro de conexão: {str(e)}"
            }


# Instância global do cliente de API
ticket_api_client = TicketAPIClient()


def create_ticket(
    user_name: str,
    issue_description: str,
    priority: str = "medium",
    status: str = "open",
    resolution: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria um novo ticket de suporte técnico via API REST pública.
    
    🔥 INTEGRAÇÃO COM SESSION MANAGER:
    O user_id é obtido automaticamente do contexto da sessão ADK.
    Após criar ticket, marca sessão como completa automaticamente.
    
    Args:
        user_name: Nome do usuário que reportou o problema
        issue_description: Descrição detalhada do problema
        priority: Prioridade do ticket (low, medium, high, critical)
        status: Status do ticket ("open" ou "closed")
        resolution: Notas de resolução (obrigatório se status="closed")
    
    Returns:
        Dicionário com informações do ticket criado
    """
    # Import local para evitar circular dependency
    from session_manager import mark_attendance_completed
    
    # 🔥 NOVO: Tentar obter user_id do contexto da thread/sessão
    user_id = _get_user_id_from_context()
    
    agent_logger.tool_call("ticket_api", "create_ticket", {
        "user_name": user_name,
        "priority": priority,
        "status": status,
        "description": issue_description[:50] + "...",
        "user_id": user_id
    })
    
    try:
        # Fazer requisição para API real
        result = ticket_api_client.create_ticket(
            user_name, 
            issue_description, 
            priority,
            status,
            resolution
        )
        
        if result["success"]:
            ticket_id = result['ticket_id']
            
            # 🔥 NOVO: MARCAR SESSÃO COMO COMPLETA
            if user_id:
                agent_logger.info("\n" + "="*70)
                agent_logger.info(f"🔄 MARCANDO SESSÃO COMO COMPLETA")
                agent_logger.info(f"   👤 User ID: {user_id}")
                agent_logger.info(f"   🎫 Ticket ID: {ticket_id}")
                
                mark_attendance_completed(user_id, ticket_id)
                
                agent_logger.success(f"✅ SESSÃO COMPLETA - Próxima mensagem = NOVO atendimento")
                agent_logger.info(f"   📊 Histórico será desconsiderado na próxima interação")
                agent_logger.info("="*70 + "\n")
            else:
                agent_logger.warning("\n⚠️  ATENÇÃO: user_id não fornecido")
                agent_logger.warning("   Sessão NÃO será marcada como completa")
                agent_logger.warning("   Histórico NÃO será resetado\n")
            
            # Log detalhado da criação
            if status == "closed":
                agent_logger.ticket_created_and_closed(
                    ticket_id, 
                    user_name, 
                    priority,
                    resolution if resolution else "Problema resolvido pelo agente"
                )
            else:
                agent_logger.ticket_created(ticket_id, user_name, priority)
            
            agent_logger.tool_result("create_ticket", True, f"Ticket {ticket_id} criado via API")
        else:
            agent_logger.tool_result("create_ticket", False, result["message"])
        
        return result
            
    except Exception as e:
        error_msg = f"Erro ao criar ticket: {str(e)}"
        agent_logger.tool_result("create_ticket", False, error_msg)
        return {
            "success": False,
            "message": error_msg
        }


def close_ticket(
    ticket_id: str,
    resolution_notes: str,
    user_id: Optional[str] = None  # 🔥 NOVO
) -> Dict[str, Any]:
    """
    Fecha um ticket de suporte técnico via API REST pública.
    
    🔥 INTEGRAÇÃO COM SESSION MANAGER:
    Após fechar ticket, marca sessão como completa.
    """
    from session_manager import mark_attendance_completed
    
    agent_logger.tool_call("ticket_api", "close_ticket", {
        "ticket_id": ticket_id,
        "resolution": resolution_notes[:50] + "...",
        "user_id": user_id
    })
    
    try:
        result = ticket_api_client.close_ticket(ticket_id, resolution_notes)
        
        if result["success"]:
            # 🔥 NOVO: Marcar sessão como completa
            if user_id:
                agent_logger.info(f"🔄 Marcando sessão como completa para user {user_id}")
                mark_attendance_completed(user_id, ticket_id)
                agent_logger.success(f"✅ Sessão marcada - próxima msg = NOVO atendimento")
            
            agent_logger.ticket_closed(ticket_id, resolution_notes)
            agent_logger.tool_result("close_ticket", True, f"Ticket {ticket_id} fechado via API")
        else:
            agent_logger.tool_result("close_ticket", False, result["message"])
        
        return result
            
    except Exception as e:
        error_msg = f"Erro ao fechar ticket: {str(e)}"
        agent_logger.tool_result("close_ticket", False, error_msg)
        return {
            "success": False,
            "message": error_msg
        }


def get_ticket_status(ticket_id: str) -> Dict[str, Any]:
    """Consulta o status de um ticket via API REST pública."""
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
            "message": error_msg
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
        "tickets": tickets
    }