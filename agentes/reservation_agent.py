"""
Agente especializado em gerenciar reservas de salas.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from tools import create_ticket
from prompts.prompt_reservation import reservation_instructions


def create_reservation_agent() -> Agent:
    """Cria o agente responsável pelas reservas."""
    return Agent(
        name="reservation_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
        ),
        instruction=reservation_instructions,
        description="Gerencia solicitações de reservas de salas",
        tools=[create_ticket],
    )
