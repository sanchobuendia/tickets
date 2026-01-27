"""
Agente especializado em buscar informações na base de conhecimento.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from rag import search_knowledge_base
from prompts.prompt_rag import rag_instructions


def create_rag_agent() -> Agent:
    """Cria o agente que consulta a base de conhecimento."""
    return Agent(
        name="knowledge_base_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
        ),
        instruction=rag_instructions,
        description="Busca soluções técnicas na base de conhecimento",
        tools=[search_knowledge_base],
    )
