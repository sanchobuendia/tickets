"""
Sistema de Chatbot Multi-Agente para Suporte Técnico
Usando Google ADK + Claude no AWS Bedrock
COM SISTEMA DE LOGGING DETALHADO
"""
import asyncio
import os
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from orchestrator import create_orchestrator_agent, ConversationState
from rag_system import KnowledgeBaseRAG
from logger import agent_logger
from tools import list_all_tickets
import sys

# Carregar variáveis de ambiente
load_dotenv()

# Configurar credenciais AWS
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-1")
os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

# Remover AWS_PROFILE para evitar conflitos
if "AWS_PROFILE" in os.environ:
    del os.environ["AWS_PROFILE"]


class TechSupportChatbot:
    def __init__(self):
        """Inicializa o chatbot com todos os componentes"""
        agent_logger.separator()
        agent_logger.info("🚀 Inicializando Sistema de Suporte Técnico Multi-Agente...")
        agent_logger.separator()
        
        # Inicializar base de conhecimento
        agent_logger.info("📚 Carregando base de conhecimento...")
        self.rag = KnowledgeBaseRAG()
        
        # Criar agente orquestrador
        agent_logger.info("🔧 Criando agentes especializados...")
        self.orchestrator = create_orchestrator_agent()
        
        # Serviço de sessão
        agent_logger.info("🔐 Configurando serviço de sessão...")
        self.session_service = InMemorySessionService()
        self.session = None  # Será criada de forma assíncrona
        
        # Runner para executar o agente
        agent_logger.info("⚙️  Configurando runner de agentes...")
        self.runner = Runner(
            app_name=self.orchestrator.name,
            agent=self.orchestrator,
            session_service=self.session_service
        )
        
        # Estado da conversa
        agent_logger.info("📊 Inicializando estado da conversa...")
        self.state = ConversationState()
        
        agent_logger.separator()
        agent_logger.info("✅ Sistema iniciado com sucesso!")
        agent_logger.separator()
    
    async def initialize_session(self):
        """Inicializa a sessão de forma assíncrona"""
        if self.session is None:
            agent_logger.info("🔄 Criando sessão de usuário...")
            self.session = await self.session_service.create_session(
                app_name=self.orchestrator.name,
                session_id="tech_support_session",
                user_id="user_123"
            )
            agent_logger.info(f"✅ Sessão criada: {self.session.id}")
    
    async def send_message(self, user_message: str) -> str:
        """
        Envia uma mensagem para o chatbot e retorna a resposta
        COM LOGGING DETALHADO DO PROCESSO
        
        Args:
            user_message: Mensagem do usuário
            
        Returns:
            Resposta do chatbot
        """
        # Garantir que a sessão está inicializada
        await self.initialize_session()
        
        # Log da mensagem do usuário
        agent_logger.user_message(user_message)
        
        # Adicionar ao histórico
        self.state.add_message("user", user_message)
        
        # Iniciar processamento
        agent_logger.agent_start("orchestrator", f"Processar: '{user_message[:50]}...'")
        
        # Criar mensagem como dict ou objeto apropriado
        try:
            from google.genai.types import Content, Part
            message_obj = Content(role="user", parts=[Part(text=user_message)])
        except:
            message_obj = {"role": "user", "content": user_message}
        
        # Executar agente - capturar resposta do generator corretamente
        bot_response = ""
        response_chunks = []
        
        agent_logger.info("🔄 Executando pipeline de agentes...")
        
        try:
            for chunk in self.runner.run(
                new_message=message_obj,
                session_id=self.session.id,
                user_id="user_123"
            ):
                response_chunks.append(chunk)
                
                # Tentar extrair conteúdo de diferentes formatos
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    if isinstance(content, str):
                        bot_response = content
                    elif hasattr(content, 'parts') and content.parts:
                        first_part = content.parts[0]
                        if hasattr(first_part, 'text'):
                            bot_response = first_part.text
                        else:
                            bot_response = str(first_part)
                    else:
                        bot_response = str(content)
                elif hasattr(chunk, 'parts'):
                    if chunk.parts:
                        first_part = chunk.parts[0]
                        if hasattr(first_part, 'text'):
                            bot_response = first_part.text
                        else:
                            bot_response = str(first_part)
                elif hasattr(chunk, 'text'):
                    bot_response = chunk.text
                elif hasattr(chunk, 'message'):
                    bot_response = chunk.message
                elif isinstance(chunk, dict):
                    bot_response = chunk.get("content") or chunk.get("text") or chunk.get("message") or chunk.get("response", "")
                elif isinstance(chunk, str):
                    bot_response = chunk
            
            # Se ainda não temos resposta, tentar converter o último chunk
            if not bot_response and response_chunks:
                last_chunk = response_chunks[-1]
                if hasattr(last_chunk, 'parts') and last_chunk.parts:
                    first_part = last_chunk.parts[0]
                    if hasattr(first_part, 'text'):
                        bot_response = first_part.text
            
            if not bot_response:
                bot_response = "Desculpe, não consegui processar sua mensagem."
                agent_logger.warning("⚠️  Resposta vazia do agente")
            
        except Exception as e:
            agent_logger.error(f"Erro ao executar agente: {str(e)}")
            bot_response = f"Erro ao processar mensagem: {str(e)}"
        
        # Finalizar agente
        agent_logger.agent_end("orchestrator", bot_response[:100])
        
        # Log da resposta do assistente
        agent_logger.assistant_message(bot_response)
        
        # Adicionar ao histórico
        self.state.add_message("assistant", bot_response)
        
        return bot_response
    
    def get_state(self) -> dict:
        """Retorna o estado atual da conversa"""
        return self.state.get_summary()
    
    async def chat_loop(self):
        """Loop interativo de chat no terminal"""
        agent_logger.separator()
        print("🎯 CHATBOT DE SUPORTE TÉCNICO")
        agent_logger.separator()
        print("\nBem-vindo ao sistema de suporte técnico!")
        print("Digite sua dúvida ou problema e eu vou te ajudar.")
        print("\nComandos especiais:")
        print("  - 'sair' ou 'exit': Encerrar o chat")
        print("  - 'tickets': Ver todos os tickets criados")
        print("  - 'estado': Ver estado da conversa atual\n")
        agent_logger.separator()
        
        while True:
            try:
                # Ler entrada do usuário
                user_input = input("\n💤 Você: ").strip()
                
                if not user_input:
                    continue
                
                # Comandos especiais
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    agent_logger.info("👋 Encerrando sistema...")
                    print("\n👋 Até logo! Espero ter ajudado.")
                    break
                
                if user_input.lower() == 'tickets':
                    agent_logger.separator()
                    tickets_info = list_all_tickets()
                    print(f"\n📋 Total de tickets: {tickets_info['total']}")
                    print(f"   🟢 Abertos: {tickets_info['open']}")
                    print(f"   🔴 Fechados: {tickets_info['closed']}")
                    
                    if tickets_info['tickets']:
                        print("\n📝 Detalhes dos tickets:")
                        for ticket_id, ticket in tickets_info['tickets'].items():
                            print(f"\n   🎫 {ticket_id}")
                            print(f"      Status: {ticket['status']}")
                            print(f"      Usuário: {ticket['user_name']}")
                            print(f"      Prioridade: {ticket['priority']}")
                            if ticket['status'] == 'closed':
                                print(f"      Resolução: {ticket['resolution_notes'][:50]}...")
                    agent_logger.separator()
                    continue
                
                if user_input.lower() == 'estado':
                    agent_logger.separator()
                    state = self.get_state()
                    print("\n📊 Estado da Conversa:")
                    print(f"   🎫 Ticket ID: {state['ticket_id'] or 'Nenhum'}")
                    print(f"   ✅ Resolvido: {'Sim' if state['problem_resolved'] else 'Não'}")
                    print(f"   👤 Usuário: {state['user_name'] or 'Não informado'}")
                    print(f"   💬 Mensagens: {state['messages_count']}")
                    agent_logger.separator()
                    continue
                
                # Enviar mensagem e obter resposta
                print()
                response = await self.send_message(user_input)
                print(f"\n🤖 Assistente: {response}")
                
                agent_logger.separator()
                
            except KeyboardInterrupt:
                agent_logger.warning("\n\n⚠️  Interrupção do usuário detectada")
                print("\n\n👋 Atendimento encerrado pelo usuário.")
                break
            except Exception as e:
                agent_logger.error(f"Erro no loop de chat: {str(e)}")
                print(f"\n❌ Erro: {str(e)}")
                print("Por favor, tente novamente.")


async def main():
    """Função principal"""
    try:
        # Criar e iniciar chatbot
        chatbot = TechSupportChatbot()
        
        # Iniciar loop de chat
        await chatbot.chat_loop()
        
    except KeyboardInterrupt:
        agent_logger.info("\n\n👋 Encerrando por interrupção do usuário...")
    except Exception as e:
        agent_logger.error(f"Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Executar aplicação
    asyncio.run(main())