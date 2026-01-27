"""
Agente que conduz o suporte técnico direto ao usuário.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from prompts.prompt_suport import suport_instructions


def create_support_agent() -> Agent:
    """Cria o agente de suporte técnico."""
    return Agent(
        name="tech_support_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
        ),
        instruction=suport_instructions,
        description="Fornece suporte técnico direto ao usuário",
    )
