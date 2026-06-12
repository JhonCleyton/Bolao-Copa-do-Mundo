import requests
import os
from typing import Optional


class WhatsAppService:
    def __init__(self):
        self.api_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.instance = os.getenv("EVOLUTION_INSTANCE", "bolao-copa")
    
    def _send_message(self, phone: str, message: str) -> bool:
        try:
            # Format phone number
            phone = phone.replace("+", "").replace("-", "").replace(" ", "")
            if not phone.startswith("55") and len(phone) == 11:
                phone = "55" + phone
            
            url = f"{self.api_url}/message/sendText/{self.instance}"
            
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "number": phone,
                "text": message,
                "options": {
                    "delay": 1200,
                    "presence": "composing"
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.status_code == 200 or response.status_code == 201
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_verification_code(self, phone: str, code: str, name: str) -> bool:
        message = f"""🎯 *Bolão Copa 2026*

Olá, {name}!

Seu código de verificação é: *{code}*

Este código expira em 10 minutos.

Se você não solicitou, ignore esta mensagem."""
        
        return self._send_message(phone, message)
    
    def send_welcome(self, phone: str, name: str) -> bool:
        message = f"""🎯 *Bolão Copa 2026*

Bem-vindo, {name}! 🎉

✅ Sua conta foi ativada!

*Próximos passos:*
• Pague R$ 100,00 de inscrição
• Pague R$ 10,00 por rodada
• Faça seus palpites

💰 Prêmio por rodada: R$ 100,00!

Boa sorte! ⚽"""
        
        return self._send_message(phone, message)
    
    def send_round_notification(self, phone: str, name: str, round_number: int,
                                 position: int, points: int, prize: float) -> bool:
        prize_text = f"R$ {prize:.2f}" if prize > 0 else "Nenhum"
        
        message = f"""🎯 *Bolão Copa 2026 - Rodada {round_number}*

Olá, {name}!

📊 *Seu resultado:*
• Pontos: {points}
• Posição: {position}º lugar
• Prêmio: {prize_text}

Boa sorte na próxima rodada! ⚽"""
        
        return self._send_message(phone, message)
    
    def send_winner_notification(self, phone: str, name: str, round_number: int,
                                  position: int, prize: float) -> bool:
        medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉"
        
        message = f"""🎯 *Bolão Copa 2026*

🎉 *PARABÉNS, {name}!* {medal}

Você venceu a rodada {round_number}!

💰 *Prêmio:* R$ {prize:.2f}

Continue participando! ⚽"""
        
        return self._send_message(phone, message)
    
    def send_match_reminder(self, phone: str, name: str, team_a: str, team_b: str, 
                            match_time: str) -> bool:
        message = f"""🎯 *Bolão Copa 2026*

Olá, {name}!

⏰ Lembrete: Falta 1 hora para:

⚽ *{team_a} x {team_b}*
🕐 {match_time}

Faça seu palpite agora! 📝"""
        
        return self._send_message(phone, message)
    
    def send_payment_reminder(self, phone: str, name: str, round_number: Optional[int] = None) -> bool:
        if round_number:
            message = f"""🎯 *Bolão Copa 2026*

Olá, {name}!

⚠️ Lembrete de pagamento:

Você ainda não pagou a rodada {round_number}.
Valor: R$ 10,00

Regularize para participar! 💰"""
        else:
            message = f"""🎯 *Bolão Copa 2026*

Olá, {name}!

⚠️ Lembrete de pagamento:

Você ainda não pagou a inscrição.
Valor: R$ 100,00

Regularize para participar! 💰"""
        
        return self._send_message(phone, message)

    # ==================== PVP BET MESSAGES ====================

    def send_pvp_challenge(self, phone: str, challenged_name: str, challenger_name: str,
                           prize_description: str, bet_type: str,
                           match_details: str = None, round_number: int = None,
                           bet_id: int = None) -> bool:
        """Send challenge notification to challenged user"""

        if bet_type == "match" and match_details:
            event_description = f"na partida *{match_details}*"
        elif bet_type == "round" and round_number:
            event_description = f"na *rodada {round_number}*"
        else:
            event_description = "no *campeonato inteiro*"

        message = f"""🎯 *Bolão Copa 2026 - Desafio PVP*

Olá, {challenged_name}! 🏆

⚡ *{challenger_name}* te desafiou!

🎁 *Prêmio:* {prize_description}
📅 *Aposta:* {event_description}

Quem fizer mais pontos vence! 💪

Entre agora no sistema e aceite o desafio!
🌐 Acesse: https://bolao.jhoncleyton.dev

ID do desafio: #{bet_id}"""

        return self._send_message(phone, message)

    def send_pvp_accepted(self, phone: str, challenger_name: str, challenged_name: str,
                          prize_description: str) -> bool:
        """Notify challenger that challenge was accepted"""

        message = f"""🎯 *Bolão Copa 2026 - Desafio Aceito!*

Olá, {challenger_name}! 🎉

✅ *{challenged_name}* aceitou seu desafio!

🎁 *Prêmio:* {prize_description}

A aposta está valendo! Boa sorte! ⚽

Que vença o melhor! 🏆"""

        return self._send_message(phone, message)

    def send_pvp_rejected(self, phone: str, challenger_name: str, challenged_name: str,
                          prize_description: str) -> bool:
        """Notify challenger that challenge was rejected"""

        message = f"""🎯 *Bolão Copa 2026 - Desafio Recusado*

Olá, {challenger_name}!

❌ *{challenged_name}* recusou seu desafio.

🎁 *Prêmio:* {prize_description}

Não desanime! Desafie outro jogador! 💪"""

        return self._send_message(phone, message)

    def send_pvp_cancelled(self, phone: str, challenged_name: str, challenger_name: str,
                           prize_description: str) -> bool:
        """Notify challenged that challenge was cancelled"""

        message = f"""🎯 *Bolão Copa 2026 - Desafio Cancelado*

Olá, {challenged_name}!

🚫 *{challenger_name}* cancelou o desafio.

🎁 *Prêmio:* {prize_description}

O desafio foi cancelado antes da sua resposta."""

        return self._send_message(phone, message)

    def send_pvp_match_result(self, phone: str, user_name: str, opponent_name: str,
                              prize_description: str, user_points: int,
                              opponent_points: int, won: bool, bet_type: str,
                              match_details: str = None) -> bool:
        """Send match/round end result to a participant"""

        medal = "🥇" if won else "🥈"
        result_text = "🎉 VOCÊ VENCEU!" if won else "😔 Você perdeu"

        if match_details:
            event = f"Partida: {match_details}"
        elif bet_type == "round":
            event = "Rodada finalizada"
        else:
            event = "Campeonato finalizado"

        message = f"""🎯 *Bolão Copa 2026 - Resultado PVP*

Olá, {user_name}! {medal}

{event}

📊 *Placar:*
• Você: {user_points} pontos
• {opponent_name}: {opponent_points} pontos

{result_text}

🎁 *Prêmio da aposta:* {prize_description}

{"Parabéns! 🏆" if won else "Mais sorte na próxima! 💪"}"""

        return self._send_message(phone, message)


# Global instance
whatsapp_service = WhatsAppService()
