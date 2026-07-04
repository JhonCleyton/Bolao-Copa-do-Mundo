import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os
from typing import Optional


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("MAIL_SERVER", os.getenv("SMTP_HOST", "smtp.gmail.com"))
        self.smtp_port = int(os.getenv("MAIL_PORT", os.getenv("SMTP_PORT", "587")))
        self.smtp_user = os.getenv("MAIL_USERNAME", os.getenv("SMTP_USER", ""))
        self.smtp_password = os.getenv("MAIL_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
        self.from_email = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("FROM_EMAIL", ""))
        self.from_name = os.getenv("MAIL_REMETENTE_NOME", os.getenv("FROM_NAME", "Bolão Copa 2026"))
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Text part
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            
            # HTML part
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _get_email_footer(self):
        """Generate professional email footer"""
        return """
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 25px; text-align: center; margin-top: 30px; border-radius: 0 0 10px 10px;">
            <p style="color: #fff; margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">
                ⚽ Bolão Copa 2026 - O Maior Bolão do Brasil
            </p>
            <p style="color: #ccc; margin: 0 0 15px 0; font-size: 12px;">
                &copy; 2026 - Todos os direitos reservados
            </p>
            <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px; margin-top: 15px;">
                <p style="color: #aaa; margin: 0 0 10px 0; font-size: 11px;">
                    Desenvolvido por <strong style="color: #4fc3f7;">Jhon Cleyton</strong> — <strong style="color: #4fc3f7;">JC Byte</strong>
                </p>
                <p style="margin: 5px 0;">
                    <a href="https://jhoncleyton.dev" style="color: #4fc3f7; text-decoration: none; font-size: 11px;">🌐 Portfólio</a> |
                    <a href="https://www.linkedin.com/in/jhon-freire" style="color: #4fc3f7; text-decoration: none; font-size: 11px;">💼 LinkedIn</a> |
                    <a href="https://wa.me/5573998547885" style="color: #4fc3f7; text-decoration: none; font-size: 11px;">💬 WhatsApp</a>
                </p>
            </div>
        </div>
        """
    
    def send_verification_code(self, to_email: str, code: str, name: str) -> bool:
        subject = "🔐 Código de Verificação - Bolão Copa 2026"
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">⚽ Bolão Copa 2026</h1>
                    <p style="color: #ccc; margin: 10px 0 0 0; font-size: 14px;">Verificação de Segurança</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #1e3c72; margin: 0 0 20px 0; font-size: 22px;">Olá, {name}! 👋</h2>
                    <p style="font-size: 16px; color: #555; margin: 0 0 25px 0;">
                        Recebemos uma solicitação de verificação para sua conta no Bolão Copa 2026.
                    </p>
                    
                    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-left: 4px solid #1e3c72; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center;">
                        <p style="margin: 0 0 15px 0; font-size: 14px; color: #666;">Seu código de verificação é:</p>
                        <div style="font-size: 36px; font-weight: bold; color: #1e3c72; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                            {code}
                        </div>
                    </div>
                    
                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0;">
                        <p style="margin: 0; color: #856404; font-size: 14px;">
                            <strong>⏰ Importante:</strong> Este código expira em <strong>10 minutos</strong>.
                        </p>
                    </div>
                    
                    <p style="font-size: 14px; color: #888; margin: 25px 0 0 0; text-align: center;">
                        Se você não solicitou este código, ignore este email ou entre em contato conosco.
                    </p>
                </div>
                
                {self._get_email_footer()}
            </div>
        </body>
        </html>
        """
        
        text = f"""
Olá, {name}!

Seu código de verificação para o Bolão Copa 2026 é: {code}

Este código expira em 10 minutos.

Se você não solicitou este código, ignore este email.

---
Bolão Copa 2026
Desenvolvido por Jhon Cleyton - JC Byte
https://jhoncleyton.dev
"""
        
        return self._send_email(to_email, subject, html, text)
    
    def send_welcome(self, to_email: str, name: str) -> bool:
        subject = "🎉 Bem-vindo ao Bolão Copa 2026!"
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">⚽ Bolão Copa 2026</h1>
                    <p style="color: #ccc; margin: 10px 0 0 0; font-size: 14px;">Bem-vindo ao Maior Bolão do Brasil!</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #1e3c72; margin: 0 0 20px 0; font-size: 22px;">Bem-vindo, {name}! 🎉</h2>
                    <p style="font-size: 16px; color: #555; margin: 0 0 25px 0;">
                        Sua conta no <strong>Bolão Copa 2026</strong> foi ativada com sucesso! Prepare-se para a emoção da maior competição de futebol do mundo.
                    </p>
                    
                    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-left: 4px solid #4caf50; padding: 20px; margin: 25px 0; border-radius: 8px;">
                        <h3 style="color: #2e7d32; margin: 0 0 15px 0; font-size: 16px;">📋 Próximos Passos:</h3>
                        <ol style="margin: 0; padding-left: 20px; color: #555;">
                            <li style="margin-bottom: 10px;">Realize o pagamento da inscrição de <strong>R$ 100,00</strong></li>
                            <li style="margin-bottom: 10px;">Pague <strong>R$ 10,00</strong> por cada rodada que deseja participar</li>
                            <li>Faça seus palpites antes do início dos jogos</li>
                        </ol>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-radius: 8px; padding: 20px; margin: 25px 0; text-align: center;">
                        <h3 style="color: #e65100; margin: 0 0 10px 0; font-size: 18px;">🏆 Prêmio por Rodada</h3>
                        <p style="font-size: 28px; font-weight: bold; color: #e65100; margin: 0;">R$ 100,00</p>
                    </div>
                    
                    <p style="font-size: 16px; color: #555; margin: 25px 0; text-align: center;">
                        Boa sorte e divirta-se! 🍀⚽
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{APP_URL}}/dashboard" style="display: inline-block; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #fff; padding: 15px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px;">
                            Acessar Meu Dashboard
                        </a>
                    </div>
                </div>
                
                {self._get_email_footer()}
            </div>
        </body>
        </html>
        """
        
        text = f"""
Olá, {name}!

Bem-vindo ao Bolão Copa 2026! Sua conta foi ativada com sucesso!

PRÓXIMOS PASSOS:
1. Realize o pagamento da inscrição de R$ 100,00
2. Pague R$ 10,00 por cada rodada que deseja participar
3. Faça seus palpites antes do início dos jogos

PRÊMIO POR RODADA: R$ 100,00!

Boa sorte e divirta-se!

Acesse: {{APP_URL}}/dashboard

---
Bolão Copa 2026
Desenvolvido por Jhon Cleyton - JC Byte
https://jhoncleyton.dev
"""
        
        return self._send_email(to_email, subject, html, text)
    
    def send_round_notification(self, to_email: str, name: str, round_number: int, 
                                 position: int, points: int, prize: float) -> bool:
        subject = f"📊 Resultado da Rodada {round_number} - Bolão Copa 2026"
        
        prize_text = f"R$ {prize:.2f}" if prize > 0 else "Nenhum"
        position_emoji = "🥇" if position == 1 else ("🥈" if position == 2 else ("🥉" if position == 3 else "🏅"))
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">⚽ Bolão Copa 2026</h1>
                    <p style="color: #ccc; margin: 10px 0 0 0; font-size: 14px;">Resultado da Rodada {round_number}</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #1e3c72; margin: 0 0 20px 0; font-size: 22px;">Olá, {name}! 👋</h2>
                    <p style="font-size: 16px; color: #555; margin: 0 0 25px 0;">
                        Confira seu desempenho na <strong>Rodada {round_number}</strong> do Bolão Copa 2026:
                    </p>
                    
                    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 12px; padding: 30px; margin: 25px 0; text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 15px;">{position_emoji}</div>
                        <p style="font-size: 14px; color: #666; margin: 0 0 5px 0;">Sua Posição</p>
                        <p style="font-size: 36px; font-weight: bold; color: #1e3c72; margin: 0;">{position}º Lugar</p>
                        
                        <div style="display: flex; justify-content: center; gap: 40px; margin-top: 25px; flex-wrap: wrap;">
                            <div style="text-align: center;">
                                <p style="font-size: 12px; color: #888; margin: 0 0 5px 0;">Pontos</p>
                                <p style="font-size: 28px; font-weight: bold; color: #28a745; margin: 0;">{points}</p>
                            </div>
                            <div style="text-align: center;">
                                <p style="font-size: 12px; color: #888; margin: 0 0 5px 0;">Prêmio</p>
                                <p style="font-size: 28px; font-weight: bold; color: #e65100; margin: 0;">{prize_text}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{APP_URL}}/ranking" style="display: inline-block; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #fff; padding: 15px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px;">
                            Ver Ranking Completo
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #888; margin: 25px 0 0 0; text-align: center;">
                        Continue participando e boa sorte nas próximas rodadas! ⚽
                    </p>
                </div>
                
                {self._get_email_footer()}
            </div>
        </body>
        </html>
        """
        
        text = f"""
Olá, {name}!

Resultado da Rodada {round_number} - Bolão Copa 2026

POSIÇÃO: {position}º Lugar
PONTOS: {points}
PRÊMIO: {prize_text}

Continue participando e boa sorte nas próximas rodadas!

---
Bolão Copa 2026
Desenvolvido por Jhon Cleyton - JC Byte
https://jhoncleyton.dev
"""
        
        return self._send_email(to_email, subject, html, text)
    
    def send_winner_notification(self, to_email: str, name: str, round_number: int,
                                  position: int, prize: float) -> bool:
        subject = f"🎉 PARABÉNS! Você ganhou na Rodada {round_number}!"
        
        position_emoji = "🥇" if position == 1 else ("🥈" if position == 2 else "🥉")
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">⚽ Bolão Copa 2026</h1>
                    <p style="color: #ccc; margin: 10px 0 0 0; font-size: 14px;">🏆 Você é um Vencedor!</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <div style="font-size: 72px; margin-bottom: 10px;">{position_emoji}</div>
                        <h2 style="color: #28a745; margin: 0; font-size: 28px;">Parabéns, {name}!</h2>
                    </div>
                    
                    <p style="font-size: 18px; color: #555; margin: 0 0 25px 0; text-align: center;">
                        Você foi um dos <strong>vencedores</strong> da <strong>Rodada {round_number}</strong> do Bolão Copa 2026!
                    </p>
                    
                    <div style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; border-radius: 12px; padding: 30px; margin: 25px 0; text-align: center;">
                        <p style="font-size: 14px; color: #155724; margin: 0 0 10px 0;">Sua Conquista</p>
                        <p style="font-size: 24px; font-weight: bold; color: #155724; margin: 0 0 20px 0;">
                            {position}º Lugar
                        </p>
                        
                        <div style="background: #fff; border-radius: 8px; padding: 20px; margin-top: 20px;">
                            <p style="font-size: 14px; color: #666; margin: 0 0 10px 0;">💰 Prêmio Ganho</p>
                            <p style="font-size: 42px; font-weight: bold; color: #28a745; margin: 0;">
                                R$ {prize:.2f}
                            </p>
                        </div>
                    </div>
                    
                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 20px; margin: 25px 0;">
                        <p style="margin: 0; color: #856404; font-size: 14px; text-align: center;">
                            <strong>💡 Próximo Passo:</strong> Entre em contato com o administrador para receber seu prêmio!
                        </p>
                    </div>
                    
                    <p style="font-size: 16px; color: #555; margin: 25px 0; text-align: center;">
                        Continue participando e boa sorte nas próximas rodadas! 🍀⚽
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{APP_URL}}/ranking" style="display: inline-block; background: linear-gradient(135deg, #28a745 0%, #34ce57 100%); color: #fff; padding: 15px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px;">
                            Ver Meu Ranking
                        </a>
                    </div>
                </div>
                
                {self._get_email_footer()}
            </div>
        </body>
        </html>
        """
        
        text = f"""
🎉 PARABÉNS, {name}! 🎉

Você foi um dos VENCEDORES da Rodada {round_number} do Bolão Copa 2026!

🏆 SUA CONQUISTA:
Posição: {position}º Lugar
Prêmio: R$ {prize:.2f}

💡 Próximo Passo: Entre em contato com o administrador para receber seu prêmio!

Continue participando e boa sorte nas próximas rodadas!

---
Bolão Copa 2026
Desenvolvido por Jhon Cleyton - JC Byte
https://jhoncleyton.dev
"""
        
        return self._send_email(to_email, subject, html, text)

    def send_password_reset(self, to_email: str, name: str, reset_url: str) -> bool:
        """Send password reset email with reset link"""
        subject = "🔐 Recuperação de Senha - Bolão Copa 2026"

        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">⚽ Bolão Copa 2026</h1>
                    <p style="color: #ccc; margin: 10px 0 0 0; font-size: 14px;">Recuperação de Senha</p>
                </div>

                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #1e3c72; margin: 0 0 20px 0; font-size: 22px;">Olá, {name}! 👋</h2>
                    <p style="font-size: 16px; color: #555; margin: 0 0 25px 0;">
                        Recebemos uma solicitação para redefinir a senha da sua conta no Bolão Copa 2026.
                    </p>

                    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-left: 4px solid #1e3c72; padding: 25px; margin: 25px 0; border-radius: 8px; text-align: center;">
                        <p style="margin: 0 0 20px 0; font-size: 14px; color: #666;">Clique no botão abaixo para criar uma nova senha:</p>
                        <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #fff; padding: 15px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px;">
                            Redefinir Minha Senha
                        </a>
                    </div>

                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0;">
                        <p style="margin: 0; color: #856404; font-size: 14px;">
                            <strong>⏰ Importante:</strong> Este link expira em <strong>1 hora</strong>.
                        </p>
                    </div>

                    <p style="font-size: 14px; color: #888; margin: 25px 0 0 0; text-align: center;">
                        Se você não solicitou esta recuperação, ignore este email. Sua senha permanece segura.
                    </p>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="font-size: 12px; color: #999; margin: 0; text-align: center;">
                            Se o botão não funcionar, copie e cole este link no navegador:<br>
                            <span style="word-break: break-all;">{reset_url}</span>
                        </p>
                    </div>
                </div>

                {self._get_email_footer()}
            </div>
        </body>
        </html>
        """

        text = f"""
Olá, {name}!

Recebemos uma solicitação para redefinir a senha da sua conta no Bolão Copa 2026.

Para criar uma nova senha, acesse o link abaixo:
{reset_url}

⏰ Este link expira em 1 hora.

Se você não solicitou esta recuperação, ignore este email.

---
Bolão Copa 2026
https://jhoncleyton.dev
"""

        return self._send_email(to_email, subject, html, text)


# Global instance
email_service = EmailService()
