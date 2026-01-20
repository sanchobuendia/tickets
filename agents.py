"""
Agentes especializados do sistema multi-agente
ATUALIZADO: Inclui agente de classificação de categoria
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from tools import create_ticket, get_ticket_status
from rag_system import search_knowledge_base
from category_code_rag import search_category_code
from prompts.prompt_rag import rag_instructions
from prompts.prompt_ticket import tickect_instructions
from prompts.prompt_suport import suport_instructions
from prompts.prompt_category_classifier import category_classifier_instructions


def create_rag_agent() -> Agent:
    """
    Agente especializado em buscar informações na base de conhecimento
    """
    return Agent(
        name="knowledge_base_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=rag_instructions,
        description="Busca soluções técnicas na base de conhecimento",
        tools=[search_knowledge_base]
    )


def create_category_classifier_agent() -> Agent:
    """
    Agente especializado em classificar e encontrar o código de categoria adequado
    NOVO: Usa RAG na collection "codigo" para encontrar o código correto
    """
    return Agent(
        name="category_classifier_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=category_classifier_instructions,
        description="Classifica o problema e encontra o código de categoria mais adequado",
        tools=[search_category_code]
    )


def create_ticket_creation_agent() -> Agent:
    """
    Agente especializado em criar tickets de suporte com status correto
    """
    return Agent(
        name="ticket_creator_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=tickect_instructions,
        description="Cria novos tickets de suporte técnico",
        tools=[create_ticket]
    )


def create_support_agent() -> Agent:
    """
    Agente de suporte técnico que tenta resolver problemas diretamente
    """
    return Agent(
        name="tech_support_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS
        ),
        instruction=suport_instructions,
        description="Fornece suporte técnico direto ao usuário"
    )