"""
Agente dedicado à criação de tickets de suporte.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from tools import create_ticket
from prompts.prompt_ticket import tickect_instructions


def create_ticket_creation_agent() -> Agent:
    """Cria o agente responsável por abrir tickets."""
    return Agent(
        name="ticket_creator_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
        ),
        instruction=tickect_instructions,
        description="Cria novos tickets de suporte técnico",
        tools=[create_ticket],
    )
