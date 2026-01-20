"""
Tools para gerenciamento de tickets via API PÚBLICA
USA JSONPlaceholder (https://jsonplaceholder.typicode.com/) como POC
ATUALIZADO: Suporta criação de tickets com status (open/closed) e resolution
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


class TicketAPIClient:
    """
    Cliente para API de Tickets usando JSONPlaceholder
    
    POC: Usa API pública gratuita - https://jsonplaceholder.typicode.com
    - Não requer autenticação
    - Aceita POST/PUT/DELETE (mas não persiste dados)
    - Retorna responses realistas
    
    Em produção: Substituir por API real do seu sistema de tickets
    """
    
    # API pública gratuita para testes
    BASE_URL = "https://jsonplaceholder.typicode.com"
    
    def __init__(self):
        agent_logger.info("🌐 Cliente de API de Tickets Inicializado")
        agent_logger.info(f"   Base URL: {self.BASE_URL}")
        
        # Cache local para simular persistência (já que JSONPlaceholder não persiste)
        self.local_cache = {}
    
    def create_ticket(
        self, 
        user_name: str, 
        issue_description: str, 
        priority: str,
        status: str = "open",
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria um ticket via API REST com status configurável
        
        Endpoint: POST /posts
        (JSONPlaceholder usa /posts como endpoint genérico de recursos)
        
        Args:
            user_name: Nome do usuário
            issue_description: Descrição do problema
            priority: Prioridade (low, medium, high, critical)
            status: Status do ticket ("open" ou "closed")
            resolution: Notas de resolução (obrigatório se status="closed")
        """
        agent_logger.info("🔄 Fazendo requisição HTTP para criar ticket...")
        
        # Gerar ID único para rastreamento local
        local_ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        
        # Payload da requisição
        payload = {
            "title": f"Suporte Técnico - {user_name}",
            "body": issue_description,
            "userId": 1,
            "priority": priority,
            "status": status,
            "localId": local_ticket_id  # ID local para rastreamento
        }
        
        # Se o ticket já está sendo criado como fechado, adicionar resolution
        if status == "closed":
            if not resolution:
                resolution = "Problema resolvido pelo agente de suporte"
            payload["resolution"] = resolution
            payload["closedAt"] = datetime.now().isoformat()
        
        agent_logger.info(f"   📤 POST {self.BASE_URL}/posts")
        agent_logger.debug(f"   📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            # Fazer requisição POST
            response = requests.post(
                f"{self.BASE_URL}/posts",
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            agent_logger.info(f"   📥 Status Code: {response.status_code}")
            
            # Verificar resposta
            if response.status_code in [200, 201]:
                data = response.json()
                agent_logger.info(f"   ✅ Resposta recebida: ID={data.get('id')}")
                
                # API retorna um ID numérico, vamos usar nosso ID personalizado
                remote_id = data.get("id")
                
                # Armazenar em cache local (já que JSONPlaceholder não persiste)
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
                
                # Adicionar resolution se fornecida
                if resolution:
                    ticket["resolution_notes"] = resolution
                    ticket["closed_at"] = datetime.now().isoformat()
                
                self.local_cache[local_ticket_id] = ticket
                
                agent_logger.info(f"   💾 Ticket armazenado em cache local")
                
                # Log destacado baseado no status
                if status == "closed":
                    agent_logger.info("\n   " + "─"*50)
                    agent_logger.info(f"   ✅ TICKET CRIADO JÁ FECHADO")
                    agent_logger.info(f"   🎫 ID: {local_ticket_id}")
                    agent_logger.info(f"   👤 Usuário: {user_name}")
                    agent_logger.info(f"   👤 Description: {issue_description}")
                    agent_logger.info(f"   ⚡ Prioridade: {priority}")
                    agent_logger.info(f"   📝 Resolução: {resolution[:50]}..." if resolution and len(resolution) > 50 else f"   📝 Resolução: {resolution}")
                    agent_logger.info("   " + "─"*50 + "\n")
                    message = f"✅ Ticket #{local_ticket_id} criado e fechado via API"
                else:
                    agent_logger.info("\n   " + "─"*50)
                    agent_logger.info(f"   📋 TICKET CRIADO (ABERTO)")
                    agent_logger.info(f"   🎫 ID: {local_ticket_id}")
                    agent_logger.info(f"   👤 Usuário: {user_name}")
                    agent_logger.info(f"   👤 Description: {issue_description}")
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
            agent_logger.error("   ⏱️  Timeout na requisição")
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
        """
        Fecha um ticket via API REST
        
        Endpoint: PUT /posts/{id}
        """
        agent_logger.info(f"🔄 Fazendo requisição HTTP para fechar ticket {ticket_id}...")
        
        # Buscar ticket no cache local
        ticket = self.local_cache.get(ticket_id)
        
        if not ticket:
            agent_logger.warning(f"   ⚠️  Ticket {ticket_id} não encontrado no cache local")
            # Tentar mesmo assim com um ID padrão
            remote_id = 1
        else:
            remote_id = ticket.get("remote_id", 1)
        
        # Payload da requisição
        payload = {
            "id": remote_id,
            "status": "closed",
            "resolution": resolution_notes,
            "closedAt": datetime.now().isoformat()
        }
        
        agent_logger.info(f"   📤 PUT {self.BASE_URL}/posts/{remote_id}")
        agent_logger.debug(f"   📦 Payload: {json.dumps(payload, indent=2)}")
        
        try:
            # Fazer requisição PUT
            response = requests.put(
                f"{self.BASE_URL}/posts/{remote_id}",
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            agent_logger.info(f"   📥 Status Code: {response.status_code}")
            
            # Verificar resposta
            if response.status_code in [200, 201]:
                data = response.json()
                agent_logger.info(f"   ✅ Ticket fechado na API")
                
                # Atualizar cache local
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
            agent_logger.error("   ⏱️  Timeout na requisição")
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
        """
        Consulta o status de um ticket via API REST
        
        Endpoint: GET /posts/{id}
        """
        agent_logger.info(f"🔄 Consultando ticket {ticket_id} na API...")
        
        # Buscar no cache local primeiro
        ticket = self.local_cache.get(ticket_id)
        
        if not ticket:
            agent_logger.warning(f"   ⚠️  Ticket {ticket_id} não encontrado no cache local")
            return {
                "success": False,
                "message": f"Ticket {ticket_id} não encontrado"
            }
        
        remote_id = ticket.get("remote_id", 1)
        
        agent_logger.info(f"   📤 GET {self.BASE_URL}/posts/{remote_id}")
        
        try:
            # Fazer requisição GET
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
    
    POC - USA API PÚBLICA:
    ----------------------
    API: JSONPlaceholder (https://jsonplaceholder.typicode.com)
    Endpoint: POST /posts
    Autenticação: Nenhuma (público)
    
    NOVA FUNCIONALIDADE:
    -------------------
    Agora suporta criação de tickets já com status "closed" para documentar
    problemas que foram resolvidos pelo agente sem necessidade de técnico.
    
    COMO FUNCIONA:
    1. Faz requisição HTTP POST para a API pública
    2. API retorna ID do recurso criado
    3. Armazena resposta em cache local (pois API não persiste)
    4. Retorna confirmação de sucesso
    
    Args:
        user_name: Nome do usuário que reportou o problema
        issue_description: Descrição detalhada do problema
        priority: Prioridade do ticket (low, medium, high, critical)
        status: Status do ticket ("open" ou "closed")
        resolution: Notas de resolução (obrigatório se status="closed")
    
    Returns:
        Dicionário com informações do ticket criado
        
    Exemplos:
        # Ticket aberto (precisa de técnico)
        create_ticket("João", "PC quebrado", "high", status="open")
        
        # Ticket já fechado (problema resolvido)
        create_ticket("Maria", "PC lento", "low", status="closed", 
                     resolution="Reinicialização resolveu o problema")
    """
    agent_logger.tool_call("ticket_api", "create_ticket", {
        "user_name": user_name,
        "priority": priority,
        "status": status,
        "description": issue_description[:50] + "..."
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
            # Log detalhado e DESTACADO da criação
            ticket_id = result['ticket_id']
            
            if status == "closed":
                # Ticket criado JÁ FECHADO - usar log especial
                agent_logger.ticket_created_and_closed(
                    ticket_id, 
                    user_name, 
                    priority,
                    resolution if resolution else "Problema resolvido pelo agente"
                )
            else:
                # Ticket criado ABERTO
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
    resolution_notes: str
) -> Dict[str, Any]:
    """
    Fecha um ticket de suporte técnico via API REST pública.
    
    NOTA: Com a nova estratégia, esta função é menos usada pois tickets
    resolvidos pelo agente são criados já com status="closed".
    
    POC - USA API PÚBLICA:
    ----------------------
    API: JSONPlaceholder (https://jsonplaceholder.typicode.com)
    Endpoint: PUT /posts/{id}
    Autenticação: Nenhuma (público)
    
    COMO FUNCIONA:
    1. Busca ticket no cache local para obter ID remoto
    2. Faz requisição HTTP PUT para a API pública
    3. API retorna confirmação de atualização
    4. Atualiza cache local com novo status
    5. Retorna confirmação de sucesso
    
    Args:
        ticket_id: ID do ticket a ser fechado
        resolution_notes: Notas sobre a resolução do problema
    
    Returns:
        Dicionário com informações do fechamento
    """
    agent_logger.tool_call("ticket_api", "close_ticket", {
        "ticket_id": ticket_id,
        "resolution": resolution_notes[:50] + "..."
    })
    
    try:
        # Fazer requisição para API real
        result = ticket_api_client.close_ticket(ticket_id, resolution_notes)
        
        if result["success"]:
            # Log detalhado do fechamento
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
    """
    Consulta o status de um ticket via API REST pública.
    
    POC - USA API PÚBLICA:
    ----------------------
    API: JSONPlaceholder (https://jsonplaceholder.typicode.com)
    Endpoint: GET /posts/{id}
    Autenticação: Nenhuma (público)
    
    Args:
        ticket_id: ID do ticket a ser consultado
    
    Returns:
        Dicionário com informações do ticket
    """
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
    """
    Lista todos os tickets do sistema (cache local)
    """
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