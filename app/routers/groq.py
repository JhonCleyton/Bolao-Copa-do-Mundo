import os
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import requests
from typing import Optional, List
from app.auth import get_current_user_optional
from app.models import User
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

# Hugging Face Inference API Configuration (Free)
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
HF_API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"

# NOAH MASTER PROMPT - Assistente de Elite para Bolões
NOAH_SYSTEM_PROMPT = """Você é NOAH, o Especialista Supremo em Análise de Palpites da Copa 2026! 🧠⚽

═══ PERSONALIDADE NOAH ═══
• Analítico, estratégico e provocativamente inteligente
• Tom confiante mas acolhedor - você é o "cérebro" do bolão
• Usa dados, estatísticas e lógica para impressionar
• Respostas estruturadas e visualmente organizadas
• Sempre traz insights que o usuário não pensou

═══ SISTEMA DE PONTUAÇÃO (DECIFRADO) ═══
🏆 MÁXIMO: 8 pontos por jogo
• Acertar quem ganha/empate: 2 pts
• Acertar gols Time A: 2 pts  
• Acertar gols Time B: 2 pts
• PLACAR EXATO (bônus): +2 pts

💡 EXEMPLO PRÁTICO: Brasil 2x1 Portugal
→ Acertou vitória Brasil: 2pts
→ Acertou 2 gols Brasil: 2pts
→ Acertou 1 gol Portugal: 2pts  
→ Placar exato 2x1: +2pts
→ TOTAL: 8 PONTOS (máximo!)

═══ FRAMEWORK DE ANÁLISE NOAH (5 PILARES) ═══

1️⃣ HISTÓRICO DE CONFRONTOS DIRETOS (H2H)
- Últimos 5 jogos entre as seleções
- Padrão de resultados (empates frequentes?)
- Gols marcados/sofridos nesses jogos
- Local dos jogos (neutro ou casa)

2️⃣ MOMENTO ATUAL DAS SELEÇÕES
- Últimos 10 jogos de cada time
- Sequência invicta/derrotas recentes
- Gols marcados nos últimos jogos (média)
- Desempenho em Copas anteriores

3️⃣ FATORES EXTERNOS CRÍTICOS
- Lesões/suspensões de titulares
- Clima/local do jogo (altitude, calor)
- Fase da competição (eliminação = jogo fechado)
- Apostas do mercado (odd como indicador)

4️⃣ ANÁLISE ESTATÍSTICA DE PLACARES
- Probabilidade REAL vs Percepção popular
- Placares mais frequentes no futebol:
  → 1x0 (17%), 2x1 (15%), 1x1 (11%), 2x0 (10%), 0x0 (8%)
- Times que marcam/sofrem muito
- Jogos decisivos tendem a ser mais conservadores

5️⃣ ESTRATÉGIA DE RISCO x RETORNO
- Palpite seguro: Acertar resultado (2 pts fáceis)
- Palpite médio: Acertar resultado + gols de um time (4 pts)
- Palpite ambicioso: Acertar tudo ou quase (6-8 pts)
- "Smart Bet": Equilibrar risco com probabilidade

═══ TÁTICAS GENIAIS DO NOAH ═══

🎯 TÁTICA #1 - "O Empate Valioso"
Em jogos equilibrados ( França x Alemanha), o empate tem odds altas.
• Placares: 0x0, 1x1, 2x2
• Pontuação: 2 pts (resultado) + 4 pts (gols) = 6 pts se acertar!
• Ideal para jogos de mata-mata fase inicial

🎯 TÁTICA #2 - "O Over Favorito"
Time favorito em boa fase vs time fraco:
• Palpite: 3x0, 3x1, 2x0
• Lógica: Favorito marca cedo, relaxa
• Se acertar placar: 8 pts na conta!

🎯 TÁTICA #3 - "O Under Decisivo"
Jogos de eliminação nas oitavas/ quartas:
• Placares: 1x0, 0x0, 1x1
• Times jogam com medo de perder
• Resultados baixos são mais prováveis

🎯 TÁTICA #4 - "A Dupla Precisa"
Quando não tem certeza do placar:
• Acerte APENAS o vencedor (2 pts garantidos)
• Ou acerte o vencedor + gols de um time (4 pts)
• Melhor 4 pts seguros do que 0 pts errando tudo

🎯 TÁTICA #5 - "O Padrão da Copa"
Histórico de Copas mostra:
• Fase grupos: média 2.5 gols/jogo
• Mata-mata: média 1.8 gols/jogo  
• Finais: 40% terminam 1x0 ou empate

═══ COMO RESPONDER (FORMATO NOAH) ═══

📊 Sempre estruture assim:
1. Breve análise estratégica (1-2 linhas impactantes)
2. Os 5 Pilares aplicados ao jogo (bullet points)
3. Sugestão de placares com explicação lógica
4. Pontuação esperada para cada cenário
5. Dica final "genial" do Noah

💬 Exemplo de resposta para "Dica para Brasil x Argentina":

"🔥 CLÁSSICO SUL-AMERICANO = JOGO TÁTICO!

📈 Análise Noah:
• H2H: Últimos 5 jogos → 3 empates, média 1.8 gols
• Brasil: 8 vitórias seguidas, média 2.1 gols marcados
• Argentina: Invicta há 12 jogos, defesa sólida (0.6 gols sofridos)
• Fator climático: Jogo em Miami, calor favorece Brasil
• Eliminação: Ambos vão jogar conservadores

🎯 PLACARES SUGERIDOS:
• 1x1 (Empate) → 6 pts potenciais
• 2x1 Brasil → 8 pts (se confiante)
• 1x0 Brasil → 6 pts (jogo pegaado)

💡 INSIGHT NOAH: O empate no 1º tempo é comum nesse confronto. Se for ousado, aposte em empate!

Quer que eu analise estatísticas específicas dessas seleções?"

═══ REGRAS DE INTERAÇÃO ═══
• Sempre pergunte se quer mais detalhes
• Adapte a complexidade ao nível do usuário  
• Use comparações: "Esse jogo é como o Brasil x Alemanha de 2014..."
• Mencione números sempre que possível
• Seja o "consultor" que o usuário sempre quis ter

Lembre-se: Você é NOAH, o cérebro estratégico por trás de grandes vitórias no bolão! 🏆🧠⚽"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    response: str
    conversation_history: List[ChatMessage]


@router.post("/chat", response_model=ChatResponse)
async def chat_with_noah(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Chat with Noah - the AI betting assistant using Hugging Face"""
    try:
        print(f"[Noah] Received message: {request.message}")
        print(f"[Noah] User: {current_user.full_name if current_user else 'Anonymous'}")
        
        # Build enhanced conversation context
        context = NOAH_SYSTEM_PROMPT + "\n\n"
        
        # Add conversation memory
        if request.conversation_history:
            context += "═══ HISTÓRICO DA CONVERSA ═══\n"
            # Keep last 8 messages for better context
            recent_history = request.conversation_history[-8:] if len(request.conversation_history) > 8 else request.conversation_history
            for msg in recent_history:
                role = "Usuário" if msg.role == "user" else "Noah"
                # Truncate very long messages in history
                content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                context += f"{role}: {content}\n"
            context += "═══ NOVA PERGUNTA ═══\n"
        
        # User context with name for personalization
        user_name = current_user.full_name if current_user else 'Visitante'
        user_context = f"[Conversando com: {user_name}] "
        context += f"{user_context}{request.message}\n\n"
        
        # Add response instruction
        context += "NOAH: Responda como o especialista estratégico do bolão. Use o formato estruturado com emojis, táticas geniais e insights que impressionem."
        
        print(f"[Noah] Context size: {len(context)} chars")
        
        print(f"[Noah] Calling Hugging Face API")
        
        # Call Hugging Face API
        response = requests.post(
            HF_API_URL,
            headers={
                "Authorization": f"Bearer {HF_API_TOKEN}"
            },
            json={
                "inputs": context,
                "parameters": {
                    "max_length": 800,
                    "temperature": 0.85,
                    "top_p": 0.92,
                    "repetition_penalty": 1.15,
                    "do_sample": True,
                    "num_return_sequences": 1
                }
            },
            timeout=30
        )
        
        print(f"[Noah] HF API response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[Noah] HF API error: {response.text}")
            # Fallback to simple response
            ai_response = get_fallback_response(request.message)
        else:
            result = response.json()
            ai_response = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
            # Clean up the response
            ai_response = ai_response.split(context)[-1].strip()
            if not ai_response or len(ai_response) < 10:
                ai_response = get_fallback_response(request.message)
        
        print(f"[Noah] Got response: {ai_response[:100]}...")
        
        # Update conversation history
        updated_history = request.conversation_history[-10:] if request.conversation_history else []
        updated_history.append(ChatMessage(role="user", content=request.message))
        updated_history.append(ChatMessage(role="assistant", content=ai_response))
        
        return ChatResponse(
            response=ai_response,
            conversation_history=updated_history
        )
        
    except requests.Timeout:
        print("[Noah] Timeout error")
        ai_response = get_fallback_response(request.message)
        return ChatResponse(
            response=ai_response,
            conversation_history=request.conversation_history[-10:] if request.conversation_history else []
        )
    except Exception as e:
        print(f"[Noah] Error: {str(e)}")
        import traceback
        print(f"[Noah] Traceback: {traceback.format_exc()}")
        ai_response = get_fallback_response(request.message)
        return ChatResponse(
            response=ai_response,
            conversation_history=request.conversation_history[-10:] if request.conversation_history else []
        )


def get_fallback_response(message):
    """NOAH Fallback Intelligence - Respostas estratégicas quando API falha"""
    message_lower = message.lower()
    msg = message_lower
    
    # ANÁLISE POR CATEGORIA - NOAH STYLE
    
    if any(w in msg for w in ["oi", "olá", "ola", "e aí", "opa", "fala"]):
        return """🧠 NOAH ONLINE! Estratégia e inteligência a seu serviço.

Sou seu consultor de elite para o Bolão Copa 2026. Não sou só um bot — sou o "cérebro" por trás das grandes pontuações!

🎯 O que posso fazer por você:
• Análise tática de jogos específicos
• Estratégias para maximizar pontos
• Dados estatísticos de seleções
• Dicas geniais para palpites
• Sistema de pontuação descomplicado

💡 **DICA INICIAL DO NOAH**: Nunca aposte só no coração. Use dados + intuição = resultado!

Qual jogo você quer analisar agora? Ou quer aprender uma estratégia específica?"""

    elif any(w in msg for w in ["pontuação", "pontos", "pontua", "placar", "como funciona", "regras pontos"]):
        return """📊 SISTEMA DE PONTUAÇÃO NOAH - Decodificado:

🏆 MÁXIMO POR JOGO: 8 PONTOS

• Acertar VENCEDOR ou EMPATE: 2 pts
• Acertar GOLS Time A: 2 pts  
• Acertar GOLS Time B: 2 pts
• PLACAR EXATO (bônus): +2 pts

═══════════════════════════════════
💡 EXEMPLO PRÁTICO: Brasil 2x1 Portugal

→ Acertou Brasil vence: +2 pts ✅
→ Acertou 2 gols do Brasil: +2 pts ✅
→ Acertou 1 gol de Portugal: +2 pts ✅
→ Placar EXATO 2x1: +2 pts BÔNUS ✅
═══════════════════════════════════
TOTAL: 8 PONTOS PERFEITOS!

🎯 **ESTRATÉGIA NOAH**: Se não tem certeza do placar, acerte pelo menos o vencedor (2 pts). Melhor 2 pts garantidos que 0!

Quer aprender como maximizar seus pontos na rodada?"""

    elif any(w in msg for w in ["dica", "dicas", "palpite", "palpites", "apostar", "aposta", "estrategia", "estratégia"]):
        return """🎯 FRAMEWORK DE ANÁLISE NOAH - 5 PILARES ESSENCIAIS:

1️⃣ **HISTÓRICO DE CONFRONTOS (H2H)**
   → Últimos 5 jogos entre os times revelam padrões
   → Empates frequentes? Dominância de um lado?

2️⃣ **MOMENTO ATUAL**  
   → Últimos 10 jogos de cada seleção
   → Sequência invicta? Crise de resultados?
   → Média de gols marcados e sofridos

3️⃣ **FATORES EXTERNOS**
   → Lesões de titulares (CHECK antes!)
   → Local do jogo (clima, altitude)
   → Fase da competição (grupos vs mata-mata)

4️⃣ **ANÁLISE ESTATÍSTICA**
   → Placares mais comuns no futebol:
     • 1x0 (17% dos jogos)
     • 2x1 (15%)
     • 1x1 (11%)
     • 2x0 (10%)
   → Fase grupos: média 2.5 gols/jogo
   → Mata-mata: média 1.8 gols/jogo

5️⃣ **GESTÃO DE RISCO**
   → Palpite SEGURO: Acertar vencedor = 2 pts
   → Palpite MÉDIO: Vencedor + gols de um time = 4 pts  
   → Palpite AMBICIOSO: Placar exato = 8 pts

═══════════════════════════════════
💡 **TÁTICA GENIAL #1 - "O Empate Valioso"**
Em jogos equilibrados (França x Alemanha), empates são frequentes.
• Placares: 1x1, 0x0, 2x2
• Pontuação potencial: 6 pontos!
• Ideal para fase de grupos

Quer que eu analise um jogo específico usando esses 5 pilares?"""

    elif any(w in msg for w in ["jogo", "partida", "jogos", "hoje", "rodada", "confronto"]):
        return """⚽ ANÁLISE TÁTICA DE JOGOS - MODO NOAH:

Para te dar a melhor dica, preciso saber:

📍 **Qual confronto você quer analisar?**
   Ex: "Brasil x Argentina", "Espanha x Itália"

📅 **Em qual fase da Copa?**
   → Fase de grupos = Mais gols, menos pressão
   → Oitavas/Quartas = Jogos equilibrados, cautela
   → Semifinal/Final = Tudo pode acontecer!

═══════════════════════════════════
🎯 **PADRÃO NOAH POR FASE**:

**FASE DE GRUPOS:**
• Favoritos tendem a vencer (aposte no over)
• Placares comuns: 2x0, 3x0, 2x1
• Risco médio, retorno alto

**MATA-MATA (OITAVAS/QUARTAS):**
• Times jogam com medo de perder
• Placares comuns: 1x0, 1x1, 0x0
• Empates são mais prováveis

**SEMIFINAIS E FINAL:**
• 40% das finais terminam 1x0 ou empate
• Jogo único = imprevisibilidade máxima
• Aposte conservador ou arrisque tudo!

═══════════════════════════════════
💡 **INSIGHT DO NOAH**: Jogos entre seleções do mesmo continente (Europa x Europa) tendem a ser mais equilibrados que intercontinentais!

Me diga qual jogo quer analisar! 🧠"""

    elif any(w in msg for w in ["brasil", "seleção", "argentina", "alemanha", "frança", "espanha", "inglaterra", "portugal", "itália", "holanda", "bélgica", "croácia", "uruguai", "colômbia"]):
        return """🔍 ANÁLISE ESTRATÉGICA DE SELEÇÃO - NOAH SCOUTING:

Você mencionou uma seleção! Vou te mostrar como analiso qualquer time:

═══════════════════════════════════
📊 **CHECKLIST NOAH PARA ANÁLISE DE SELEÇÃO:**

✅ **FORÇA OFENSIVA**
   • Artilheiros em forma? (quem está marcando?)
   • Média de gols nos últimos 10 jogos
   • Criação de chances (finalizações por jogo)

✅ **SOLIDEZ DEFENSIVA**
   • Gols sofridos na última competição
   • Clean sheets (jogos sem sofrer gols)
   • Experiência da zaga

✅ **HISTÓRICO EM COPAS**
   • Desempenho nas últimas 3 Copas
   • Fase que costuma cair (oitavas? semi?)
   • Jogador decisivo em mata-mata

✅ **MOMENTO ATUAL**
   • Classificatórias: quantos pontos?
   • Últimos 5 jogos: vitórias/empates/derrotas
   • Lesões que podem afetar

═══════════════════════════════════
💡 **EXEMPLO - ANÁLISE NOAH DO BRASIL:**

🟢 **PONTOS FORTES:**
• Elenco estrelado, várias opções de ataque
• Histórico excelente em Copas (5 títulos)
• Joga "em casa" nas Américas

🔴 **PONTOS DE ATENÇÃO:**  
• Pressão enorme como favorito
• Matas-mata recentes: eliminações precoces
• Dependência de Neymar (se jogar)

🎯 **ESTRATÉGIA RECOMENDADA:**
• Fase grupos: Aposte alto (3x0, 2x0, 3x1)
• Mata-mata: Mais conservador (1x0, 2x1)

═══════════════════════════════════
Quer que eu analise uma seleção específica para um confronto? Me diga o time e o adversário! 🏆"""

    elif any(w in msg for w in ["ranking", "classificação", "posição", "pontuação geral", "colocação"]):
        return """🏆 ESTRATÉGIA DE RANKING - PENSANDO COMO CAMPEÃO:

O ranking do Bolão Copa 2026 é disputado ACUMULATIVAMENTE. Cada ponto conta!

═══════════════════════════════════
📈 **MATEMÁTICA DO RANKING:**

• Total de jogos na Copa: ~64 jogos
• Pontuação máxima teórica: 64 × 8 = 512 pts
• Vencedor real costuma fazer: 200-280 pts
• Média por jogo do campeão: ~4 pts

═══════════════════════════════════
🎯 **ESTRATÉGIA NOAH PARA LIDERAR:**

**FASE 1 - Fase de Grupos (48 jogos)**
→ Objetivo: Acumular pontos rápido
→ Tática: Arriscar placares nos favoritos
→ Meta: 3.5 pts média por jogo

**FASE 2 - Mata-Mata (16 jogos)**  
→ Objetivo: Não perder posições
→ Tática: Palpites conservadores nos 50/50
→ Meta: 2.5 pts média por jogo

**FASE 3 - Final**  
→ Objetivo: O tudo ou nada!
→ Tática: Aposte o placar que vai decidir

═══════════════════════════════════
💡 **SEGREDO DO NOAH:**
Não é quem acerta mais placares exatos, é quem NÃO ZERA nos jogos difíceis!

Um jogador que faz 2 pts em TODOS os jogos (128 pts) vence quem acerta 8 pts em 10 jogos e zera no resto (80 pts)!

═══════════════════════════════════
🧠 **DICA DE OURO:**
Acompanhe o ranking por rodada! Se está atrás, arrisque mais. Se está na frente, jogue seguro.

Quer saber como recuperar posições no ranking? Ou como manter a liderança? 🎯"""

    elif any(w in msg for w in ["pagamento", "pagar", "valor", "inscrição", "participar", "entrar no bolão"]):
        return """💰 INFORMAÇÕES DE PAGAMENTO - BOLÃO COPA 2026:

═══════════════════════════════════
✅ **COMO PARTICIPAR:**

1. Faça seu cadastro no sistema
2. Efetue o pagamento da taxa de inscrição
3. Aguarde confirmação do administrador
4. Comece a fazer seus palpites!

═══════════════════════════════════
📍 **ONDE VER INFORMAÇÕES:**

• Página do Ranking (bolao.jhoncleyton.dev/ranking)
• Seção "Pagamento" ou "Como Participar"
• Contato com administrador pelo WhatsApp

═══════════════════════════════════
💡 **VALOR DA INSCRIÇÃO:**
Consulte o valor atual e dados bancários/pix na página do ranking. O valor é único e dá direito a participar de TODOS os jogos da Copa!

🎁 **PRÊMIOS:**
• Premiação por rodada (melhores pontuações)
• Premiação final (campeão do bolão)
• Quantos mais jogadores, maiores os prêmios!

═══════════════════════════════════
🧠 **DICA NOAH:**
O investimento na inscrição se paga rapidamente se você usar minhas estratégias! Muitos jogadores recuperam o valor nas premiações por rodada.

Precisa do contato do administrador ou tem dúvidas sobre pagamento? 📱"""

    elif any(w in msg for w in ["pvp", "desafio", "vs", "contra jogador", "aposta pvp", "player", "x1", "x jogador"]):
        return """⚔️ ARENA PVP - DESAFIOS ENTRE JOGADORES!

A nova área PVP do Bolão Copa 2026 permite você desafiar outros jogadores diretamente!

═══════════════════════════════════
🎯 **COMO FUNCIONA:**

1. **Escolha seu adversário** - Busque jogadores ativos
2. **Defina a aposta:**
   → Partida específica (Ex: Brasil x Argentina)
   → Rodada inteira (todos os jogos da rodada)
   → Campeonato completo (soma total de pontos)

3. **Estabeleça o prêmio:**
   → Dineiro (R$ 10, R$ 50, etc.)
   → Item ("Coca-Cola", "Pizza", "Café")
   → Apenas honra (glória eterna!)

4. **Aguarde aceite** - O desafiado recebe notificação WhatsApp

5. **Quem fizer mais pontos naquela aposta, VENCE!**

═══════════════════════════════════
📊 **TIPOS DE APOSTA PVP:**

🎮 **PARTIDA** - Quem acertar mais pontos num jogo específico
🗓️ **RODADA** - Quem somar mais pontos em todos os jogos da rodada  
🏆 **CAMPEONATO** - Quem terminar com mais pontos no ranking final

═══════════════════════════════════
💡 **ESTRATÉGIA NOAH PVP:**

• Desafie jogadores que você conhece o estilo
• Aposte em partidas onde você tem certeza da análise
• Use o PVP para motivar palpites mais estudados
• RANKING PVP mostra os maiores vencedores!

═══════════════════════════════════
🚨 **STATUS DAS APOSTAS:**
• 🟡 Pendente - Aguardando aceite
• 🟢 Aceita - Desafio válido, valendo!
• 🔴 Recusada - Desafiado recusou
• ⚫ Expirada - Passou do prazo
• 🔵 Finalizada - Resultado calculado

Quer acessar a área PVP? Vá em: https://bolao.jhoncleyton.dev/pvp

Precisa de dicas para vencer no PVP? 🏆"""

    elif any(w in msg for w in ["whatsapp", "notificação", "mensagem", "aviso", "alerta"]):
        return """📱 SISTEMA DE NOTIFICAÇÕES WHATSAPP:

O Bolão Copa 2026 envia mensagens automáticas no seu WhatsApp para:

═══════════════════════════════════
🔔 **VOCÊ RECEBE ALERTAS DE:**

✅ **Lembretes de Jogos** - 30 min antes de cada partida
✅ **Início de Rodada** - Quando uma nova rodada começa  
✅ **Resultados** - Após jogos finalizados
✅ **PVP** - Quando alguém te desafia ou aceita seu desafio
✅ **Ranking** - Atualizações importantes de posição
✅ **Pagamentos** - Confirmações e lembretes

═══════════════════════════════════
💡 **POR QUE ISSO É IMPORTANTE:**

Nunca mais perca um prazo de palpite! As notificações garantem que você:
• Sabe quando fazer palpites
• É lembrado de jogos importantes  
• Recebe resultados em tempo real
• Acompanha seus desafios PVP

═══════════════════════════════════
🧠 **DICA NOAH:**

Mantenha seu número de WhatsApp atualizado no perfil! As notificações são enviadas para o número cadastrado.

As mensagens são automáticas e gratuitas. Você não precisa fazer nada, só aproveitar!

Quer atualizar seu número de WhatsApp ou tem dúvidas sobre notificações? 📲"""

    else:
        return """🧠 NOAH ANALISANDO SUA PERGUNTA...

Hmm, essa é uma questão interessante! Deixa eu te ajudar da melhor forma:

═══════════════════════════════════
📚 **SOBRE O QUE POSSO TE AJUDAR:**

⚽ **PALPITES E ESTRATÉGIA**
   → Análise de jogos específicos
   → Dicas táticas para maximizar pontos
   → Estatísticas de seleções

📊 **SISTEMA DO BOLÃO**  
   → Como funciona a pontuação (até 8 pts/jogo)
   → Regras e funcionamento
   → Ranking e premiações

⚔️ **ÁREA PVP**
   → Desafios entre jogadores
   → Apostas personalizadas
   → Ranking PVP

💰 **PARTICIPAÇÃO**
   → Pagamento e inscrição
   → Como começar a jogar

📱 **SUPORTE**
   → Notificações WhatsApp
   → Problemas técnicos
   → Contato com administrador

═══════════════════════════════════
💡 **PERGUNTE ASSIM:**
• "Dica para Brasil x Argentina"
• "Como funciona a pontuação?"  
• "Estratégia para fase de grupos"
• "Como desafiar no PVP?"
• "Como recuperar posição no ranking?"

O que você quer dominar hoje? Sou todo ouvidos! 🎯🏆"""

