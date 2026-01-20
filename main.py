"""
Sistema de Chatbot Multi-Agente para Suporte Técnico
🔥 CORRIGIDO: Usa user_id ao invés de session_id
🔥 NOVO: Suporta múltiplos problemas na mesma mensagem
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

if "AWS_PROFILE" in os.environ:
    del os.environ["AWS_PROFILE"]


class TechSupportChatbot:
    def __init__(self, user_id: str = "user_123"):
        """
        Inicializa o chatbot
        
        Args:
            user_id: ID único do usuário (ex: número telefone, email, etc)
        """
        self.user_id = user_id  # 🔥 ID do usuário (não session_id)
        
        agent_logger.separator()
        agent_logger.info("🚀 Inicializando Sistema de Suporte Técnico Multi-Agente...")
        agent_logger.info(f"   👤 User ID: {user_id}")
        agent_logger.separator()
        
        # Inicializar base de conhecimento
        agent_logger.info("📚 Carregando base de conhecimento...")
        self.rag = KnowledgeBaseRAG()
        
        # Criar agente orquestrador
        agent_logger.info("🔧 Criando agentes especializados...")
        self.orchestrator = create_orchestrator_agent()
        
        # Serviço de sessão do ADK
        agent_logger.info("📝 Configurando serviço de sessão ADK...")
        self.session_service = InMemorySessionService()
        self.adk_session = None
        
        # Runner
        agent_logger.info("⚙️ Configurando runner de agentes...")
        self.runner = Runner(
            app_name=self.orchestrator.name,
            agent=self.orchestrator,
            session_service=self.session_service
        )
        
        # Estado da conversa COM user_id
        agent_logger.info("📊 Inicializando estado da conversa...")
        self.state = ConversationState(user_id=self.user_id)
        
        agent_logger.separator()
        agent_logger.info("✅ Sistema iniciado com sucesso!")
        agent_logger.separator()
    
    async def initialize_adk_session(self):
        """Inicializa a sessão do ADK (framework)"""
        if self.adk_session is None:
            agent_logger.info("📄 Criando sessão ADK...")
            self.adk_session = await self.session_service.create_session(
                app_name=self.orchestrator.name,
                session_id=f"adk_session_{self.user_id}",  # Session do ADK != user_id
                user_id=self.user_id  # 🔥 Mas vinculado ao user_id
            )
            agent_logger.info(f"✅ Sessão ADK criada: {self.adk_session.id}")
    
    async def send_message(self, user_message: str) -> str:
        """
        Envia mensagem e retorna resposta
        🔥 ATUALIZADO: Verifica reset de contexto baseado em user_id
        
        Args:
            user_message: Mensagem do usuário (pode conter múltiplos problemas)
            
        Returns:
            Resposta do chatbot
        """
        await self.initialize_adk_session()
        
        # 🔥 VERIFICAR SE DEVE RESETAR CONTEXTO (baseado em user_id)
        if self.state.should_reset_context():
            agent_logger.warning("\n" + "🔥"*35)
            agent_logger.warning("🔄 NOVA SESSÃO DETECTADA - RESETANDO CONTEXTO")
            agent_logger.warning("🔥"*35)
            agent_logger.warning(f"   👤 User ID: {self.user_id}")
            agent_logger.warning(f"   🎫 Último(s) ticket(s): {self.state.ticket_id}")
            agent_logger.warning(f"   📋 Ação: Limpando histórico de problemas anteriores")
            agent_logger.warning(f"   📨 Mantendo: Apenas mensagem atual")
            agent_logger.warning("🔥"*35 + "\n")
            
            self.state.clear_history_except_current()
        else:
            agent_logger.info("📊 Sessão contínua - mantendo contexto completo")
        
        # Log da mensagem
        agent_logger.user_message(user_message)
        
        # Adicionar ao histórico
        self.state.add_message("user", user_message)
        
        # Obter histórico filtrado
        filtered_history = self.state.get_filtered_history()
        agent_logger.info(f"\n📊 HISTÓRICO PARA O LLM:")
        agent_logger.info(f"   Total de mensagens: {len(filtered_history)}")
        if len(filtered_history) < len(self.state.conversation_history):
            agent_logger.info(f"   ⚠️  Filtrado de {len(self.state.conversation_history)} para {len(filtered_history)}")
            agent_logger.info(f"   📌 Problemas anteriores DESCONSIDERADOS\n")
        else:
            agent_logger.info(f"   ✅ Contexto completo mantido\n")
        
        # Processar
        agent_logger.agent_start("orchestrator", f"Processar: '{user_message[:50]}...'")
        
        # Criar mensagem
        try:
            from google.genai.types import Content, Part
            message_obj = Content(role="user", parts=[Part(text=user_message)])
        except:
            message_obj = {"role": "user", "content": user_message}
        
        # Executar agente
        bot_response = ""
        response_chunks = []
        
        agent_logger.info("📄 Executando pipeline de agentes...")
        agent_logger.info(f"   👤 User ID sendo processado: {self.user_id}")
        
        # 🔥 NOVO: Definir user_id no contexto global antes de executar
        from tools import set_current_user_id
        set_current_user_id(self.user_id)
        
        try:
            for chunk in self.runner.run(
                new_message=message_obj,
                session_id=self.adk_session.id,
                user_id=self.user_id  # 🔥 PASSA user_id para o runner
            ):
                response_chunks.append(chunk)
                
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
        
        # Finalizar
        agent_logger.agent_end("orchestrator", bot_response[:100])
        agent_logger.assistant_message(bot_response)
        
        # Adicionar resposta ao histórico
        self.state.add_message("assistant", bot_response)
        
        return bot_response
    
    def get_state(self) -> dict:
        """Retorna estado atual"""
        return self.state.get_summary()
    
    async def chat_loop(self):
        """Loop interativo de chat"""
        agent_logger.separator()
        print("🎯 CHATBOT DE SUPORTE TÉCNICO")
        agent_logger.separator()
        print("\nBem-vindo ao sistema de suporte técnico!")
        print("Digite sua dúvida ou problema e eu vou te ajudar.")
        print("\n💡 DICA: Você pode reportar MÚLTIPLOS problemas numa mesma mensagem!")
        print("   Exemplo: 'PC lento E impressora travada E email não abre'")
        print("   O sistema vai tratar cada problema separadamente.\n")
        print("\nComandos especiais:")
        print("  - 'sair' ou 'exit': Encerrar o chat")
        print("  - 'tickets': Ver todos os tickets criados")
        print("  - 'estado': Ver estado da conversa atual")
        print("  - 'reset': Ver se contexto será resetado\n")
        agent_logger.separator()
        
        while True:
            try:
                user_input = input("\n👤 Você: ").strip()
                
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
                        print("\n🔍 Detalhes dos tickets:")
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
                    print(f"   👤 User ID: {state['user_id']}")
                    print(f"   🔄 Estado Sessão: {state['session_state']}")
                    print(f"   🎫 Ticket ID(s): {state['ticket_id'] or 'Nenhum'}")
                    print(f"   ✅ Resolvido: {'Sim' if state['problem_resolved'] else 'Não'}")
                    print(f"   👤 Usuário: {state['user_name'] or 'Não informado'}")
                    print(f"   💬 Mensagens: {state['messages_count']}")
                    print(f"   🔄 Reset Necessário: {'SIM' if state['should_reset'] else 'NÃO'}")
                    agent_logger.separator()
                    continue
                
                if user_input.lower() == 'reset':
                    agent_logger.separator()
                    will_reset = self.state.should_reset_context()
                    print("\n🔄 Verificação de Reset:")
                    print(f"   👤 User ID: {self.user_id}")
                    print(f"   🎫 Último Ticket: {self.state.ticket_id}")
                    if will_reset:
                        print(f"   ⚠️  PRÓXIMA MENSAGEM = NOVA SESSÃO")
                        print(f"   📋 Histórico de problemas anteriores será DESCONSIDERADO")
                    else:
                        print(f"   ✅ Sessão contínua - histórico mantido")
                    agent_logger.separator()
                    continue
                
                # Enviar mensagem
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
        # 🔥 IMPORTANTE: user_id deveria vir de uma fonte real
        # Ex: número do WhatsApp, email, ID do banco, etc
        user_id = input("Digite seu ID de usuário (ex: telefone, email): ").strip()
        if not user_id:
            user_id = "user_terminal_default"
            print(f"✅ Usando ID padrão: {user_id}\n")
        
        chatbot = TechSupportChatbot(user_id=user_id)
        await chatbot.chat_loop()
        
    except KeyboardInterrupt:
        agent_logger.info("\n\n👋 Encerrando por interrupção do usuário...")
    except Exception as e:
        agent_logger.error(f"Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())