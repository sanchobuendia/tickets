"""
Sistema de Logging customizado para rastrear agentes e sub-agentes
"""
import logging
from datetime import datetime
from typing import Optional
import colorama
from colorama import Fore, Style, Back

# Inicializar colorama
colorama.init(autoreset=True)


class AgentLogger:
    """Logger customizado para rastrear chamadas de agentes"""
    
    def __init__(self, name: str = "TechSupport"):
        self.name = name
        self.indent_level = 0
        self.setup_logger()
    
    def setup_logger(self):
        """Configura o logger"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remover handlers existentes
        self.logger.handlers.clear()
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # Formato customizado
        formatter = logging.Formatter(
            '%(message)s'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _get_indent(self) -> str:
        """Retorna indentação baseada no nível"""
        return "  " * self.indent_level
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp formatado"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def agent_start(self, agent_name: str, task: str = ""):
        """Log quando um agente inicia"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{indent}{Fore.GREEN}🤖 [{timestamp}] AGENTE INICIADO: {Style.BRIGHT}{agent_name}")
        if task:
            print(f"{indent}{Fore.YELLOW}   📋 Tarefa: {task}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        self.indent_level += 1
    
    def agent_end(self, agent_name: str, result: str = ""):
        """Log quando um agente termina"""
        self.indent_level = max(0, self.indent_level - 1)
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"\n{indent}{Fore.MAGENTA}{'─'*80}")
        print(f"{indent}{Fore.GREEN}✅ [{timestamp}] AGENTE FINALIZADO: {Style.BRIGHT}{agent_name}")
        if result:
            print(f"{indent}{Fore.YELLOW}   📝 Resultado: {result[:100]}...")
        print(f"{indent}{Fore.MAGENTA}{'─'*80}{Style.RESET_ALL}\n")
    
    def subagent_call(self, parent: str, subagent: str, reason: str = ""):
        """Log quando um sub-agente é chamado"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"{indent}{Fore.BLUE}├── [{timestamp}] {parent} → {Fore.CYAN}{Style.BRIGHT}{subagent}")
        if reason:
            print(f"{indent}{Fore.BLUE}│   {Fore.YELLOW}💭 Motivo: {reason}")
    
    def tool_call(self, agent_name: str, tool_name: str, params: dict = None):
        """Log quando uma ferramenta é chamada"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"{indent}{Fore.YELLOW}🔧 [{timestamp}] {agent_name} → Ferramenta: {Style.BRIGHT}{tool_name}")
        if params:
            print(f"{indent}   📊 Parâmetros: {params}")
    
    def tool_result(self, tool_name: str, success: bool, result: str = ""):
        """Log do resultado de uma ferramenta"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        status = f"{Fore.GREEN}✓ Sucesso" if success else f"{Fore.RED}✗ Erro"
        print(f"{indent}   {status} [{timestamp}] {tool_name}")
        if result:
            print(f"{indent}   {Fore.WHITE}📄 {result[:100]}")
    
    def category_classified(self, codigo: str, grupo: str, descricao: str):
        """Log específico para classificação de categoria - NOVO"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"\n{indent}{Back.CYAN}{Fore.BLACK} CATEGORIA CLASSIFICADA {Style.RESET_ALL}")
        print(f"{indent}{Fore.CYAN}├─ 🔢 Código: {Style.BRIGHT}{codigo}")
        print(f"{indent}{Fore.CYAN}├─ 📁 Grupo: {grupo}")
        print(f"{indent}{Fore.CYAN}├─ 📝 Descrição: {descricao[:60]}...")
        print(f"{indent}{Fore.CYAN}└─ 📅 [{timestamp}]\n")
    
    def user_message(self, message: str):
        """Log de mensagem do usuário"""
        timestamp = self._get_timestamp()
        print(f"\n{Back.BLUE}{Fore.WHITE} [{timestamp}] 💬 USUÁRIO {Style.RESET_ALL}")
        print(f"{Fore.WHITE}├─ {message}\n")
    
    def assistant_message(self, message: str):
        """Log de mensagem do assistente"""
        timestamp = self._get_timestamp()
        print(f"\n{Back.GREEN}{Fore.BLACK} [{timestamp}] 🤖 ASSISTENTE {Style.RESET_ALL}")
        print(f"{Fore.WHITE}├─ {message[:200]}...\n" if len(message) > 200 else f"{Fore.WHITE}├─ {message}\n")
    
    def info(self, message: str):
        """Log de informação geral"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        print(f"{indent}{Fore.WHITE}ℹ️  [{timestamp}] {message}")
    
    def warning(self, message: str):
        """Log de aviso"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        print(f"{indent}{Fore.YELLOW}⚠️  [{timestamp}] AVISO: {message}")
    
    def error(self, message: str):
        """Log de erro"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        print(f"{indent}{Fore.RED}❌ [{timestamp}] ERRO: {message}")
    
    def debug(self, message: str):
        """Log de debug"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        print(f"{indent}{Fore.LIGHTBLACK_EX}🔍 [{timestamp}] DEBUG: {message}")
    
    def success(self, message: str):
        """Log de sucesso - NOVO"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        print(f"{indent}{Fore.GREEN}✅ [{timestamp}] {message}")
    
    def ticket_created(self, ticket_id: str, user: str, priority: str, codigo: str = None):
        """Log específico para criação de ticket ABERTO - ATUALIZADO"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"\n{indent}{Back.GREEN}{Fore.BLACK} TICKET CRIADO (ABERTO) {Style.RESET_ALL}")
        print(f"{indent}{Fore.GREEN}├─ 🎫 ID: {Style.BRIGHT}{ticket_id}")
        print(f"{indent}{Fore.GREEN}├─ 👤 Usuário: {user}")
        print(f"{indent}{Fore.GREEN}├─ ⚡ Prioridade: {priority}")
        
        if codigo:  # NOVO
            print(f"{indent}{Fore.GREEN}├─ 🔢 Categoria: {Style.BRIGHT}{codigo}")
        
        print(f"{indent}{Fore.GREEN}├─ ⏳ Status: ABERTO - Aguardando técnico")
        print(f"{indent}{Fore.GREEN}└─ 📅 [{timestamp}]\n")
    
    def ticket_created_and_closed(self, ticket_id: str, user: str, priority: str, resolution: str, codigo: str = None):
        """Log específico para ticket criado JÁ FECHADO - ATUALIZADO"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        # Banner SUPER destacado para ticket fechado
        print(f"\n{indent}{Fore.GREEN}{'█'*80}")
        print(f"{indent}{Back.GREEN}{Fore.BLACK}{Style.BRIGHT} 🎫 TICKET CRIADO E FECHADO - PROBLEMA RESOLVIDO ✅ {Style.RESET_ALL}")
        print(f"{indent}{Fore.GREEN}{'█'*80}")
        print(f"{indent}{Fore.GREEN}█  ")
        print(f"{indent}{Fore.GREEN}█  🎫 ID: {Style.BRIGHT}{ticket_id}")
        print(f"{indent}{Fore.GREEN}█  👤 Usuário: {user}")
        print(f"{indent}{Fore.GREEN}█  ⚡ Prioridade: {priority}")
        
        if codigo:  # NOVO
            print(f"{indent}{Fore.GREEN}█  🔢 Categoria: {Style.BRIGHT}{codigo}")
        
        print(f"{indent}{Fore.GREEN}█  ✅ Status: FECHADO")
        print(f"{indent}{Fore.GREEN}█  📝 Resolução: {resolution[:60]}{'...' if len(resolution) > 60 else ''}")
        print(f"{indent}{Fore.GREEN}█  📅 [{timestamp}]")
        print(f"{indent}{Fore.GREEN}█  ")
        print(f"{indent}{Fore.GREEN}{'█'*80}\n")
    
    def ticket_closed(self, ticket_id: str, resolution: str, codigo: str = None):
        """Log específico para fechamento de ticket - ATUALIZADO"""
        indent = self._get_indent()
        timestamp = self._get_timestamp()
        
        print(f"\n{indent}{Back.MAGENTA}{Fore.WHITE} TICKET FECHADO {Style.RESET_ALL}")
        print(f"{indent}{Fore.MAGENTA}├─ 🎫 ID: {Style.BRIGHT}{ticket_id}")
        
        if codigo:  # NOVO
            print(f"{indent}{Fore.MAGENTA}├─ 🔢 Categoria: {codigo}")
        
        print(f"{indent}{Fore.MAGENTA}├─ ✅ Resolução: {resolution[:80]}...")
        print(f"{indent}{Fore.MAGENTA}└─ 📅 [{timestamp}]\n")
    
    def separator(self):
        """Imprime separador visual"""
        print(f"\n{Fore.CYAN}{'═'*80}{Style.RESET_ALL}\n")


# Instância global do logger
agent_logger = AgentLogger()