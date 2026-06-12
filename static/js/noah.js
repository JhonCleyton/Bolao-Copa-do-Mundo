/**
 * Noah - AI Assistant for Bolão Copa 2026
 * Powered by Groq AI
 */

class NoahAssistant {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.conversationHistory = [];
        this.init();
    }

    init() {
        this.createElements();
        this.attachEventListeners();
        this.addWelcomeMessage();
    }

    createElements() {
        // Create mascot button
        const mascot = document.createElement('div');
        mascot.className = 'noah-mascot';
        mascot.id = 'noah-mascot';
        mascot.innerHTML = `
            <span class="noah-mascot-emoji">⚽🤖</span>
            <span class="noah-badge" id="noah-badge">1</span>
        `;
        document.body.appendChild(mascot);

        // Create chat container
        const chatContainer = document.createElement('div');
        chatContainer.className = 'noah-chat-container';
        chatContainer.id = 'noah-chat';
        chatContainer.innerHTML = `
            <div class="noah-header">
                <div class="noah-avatar">🤖</div>
                <div class="noah-info">
                    <p class="noah-name">Noah</p>
                    <span class="noah-status">
                        <span class="noah-status-dot"></span>
                        Online - Assistente de Palpites
                    </span>
                </div>
                <button class="noah-close" id="noah-close">&times;</button>
            </div>
            <div class="noah-messages" id="noah-messages">
                <div class="noah-welcome">
                    <div class="noah-welcome-emoji">⚽🤖</div>
                    <p class="noah-welcome-text">
                        Olá! Sou o Noah, seu assistente para o Bolão Copa 2026!<br>
                        Posso ajudar com dicas de palpites, estatísticas e muito mais!
                    </p>
                </div>
            </div>
            <div class="noah-quick-actions" id="noah-quick-actions">
                <button class="noah-quick-btn" data-message="Quais os jogos de hoje?">📅 Jogos Hoje</button>
                <button class="noah-quick-btn" data-message="Como funciona a pontuação?">❓ Como Funciona</button>
                <button class="noah-quick-btn" data-message="Dê uma dica de palpite!">💡 Dica de Palpite</button>
                <button class="noah-quick-btn" data-message="Quais as regras do bolão?">📋 Regras</button>
            </div>
            <div class="noah-input-container">
                <input type="text" class="noah-input" id="noah-input" placeholder="Digite sua pergunta..." maxlength="500">
                <button class="noah-send-btn" id="noah-send">
                    <i class="bi bi-send-fill"></i>
                </button>
            </div>
        `;
        document.body.appendChild(chatContainer);
    }

    attachEventListeners() {
        // Mascot click
        document.getElementById('noah-mascot').addEventListener('click', () => {
            this.toggleChat();
        });

        // Close button
        document.getElementById('noah-close').addEventListener('click', () => {
            this.closeChat();
        });

        // Send button
        document.getElementById('noah-send').addEventListener('click', () => {
            this.sendMessage();
        });

        // Input enter key
        document.getElementById('noah-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // Quick action buttons
        document.querySelectorAll('.noah-quick-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const message = e.target.dataset.message;
                this.sendMessage(message);
            });
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChat();
            }
        });
    }

    toggleChat() {
        this.isOpen = !this.isOpen;
        const chat = document.getElementById('noah-chat');
        const mascot = document.getElementById('noah-mascot');
        const badge = document.getElementById('noah-badge');

        if (this.isOpen) {
            chat.classList.add('active');
            mascot.classList.add('active');
            badge.style.display = 'none';
            document.getElementById('noah-input').focus();
            
            // Scroll to bottom
            this.scrollToBottom();
        } else {
            this.closeChat();
        }
    }

    closeChat() {
        this.isOpen = false;
        document.getElementById('noah-chat').classList.remove('active');
        document.getElementById('noah-mascot').classList.remove('active');
    }

    async sendMessage(predefinedMessage = null) {
        const input = document.getElementById('noah-input');
        const message = predefinedMessage || input.value.trim();

        if (!message) return;

        // Clear input if not predefined
        if (!predefinedMessage) {
            input.value = '';
        }

        // Add user message
        this.addMessage(message, 'user');

        // Show typing indicator
        this.showTyping();

        // Disable send button
        const sendBtn = document.getElementById('noah-send');
        sendBtn.disabled = true;

        try {
            // Call API
            const response = await fetch('/api/groq/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error('API Error');
            }

            const data = await response.json();

            // Hide typing indicator
            this.hideTyping();

            // Add AI response
            this.addMessage(data.response, 'assistant');

            // Update conversation history
            this.conversationHistory = data.conversation_history;

        } catch (error) {
            console.error('Error:', error);
            this.hideTyping();
            this.addMessage(
                "Desculpe! Tive um problema ao processar sua pergunta. Tente novamente em alguns segundos! ⚽",
                'assistant'
            );
        } finally {
            sendBtn.disabled = false;
        }
    }

    addMessage(text, role) {
        const messagesContainer = document.getElementById('noah-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `noah-message ${role}`;
        
        const time = new Date().toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        // Convert markdown-like formatting
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');

        messageDiv.innerHTML = `
            ${formattedText}
            <span class="noah-message-time">${time}</span>
        `;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        // Store message
        this.messages.push({ text, role, time });
    }

    showTyping() {
        const messagesContainer = document.getElementById('noah-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'noah-typing';
        typingDiv.id = 'noah-typing-indicator';
        typingDiv.innerHTML = `
            <span class="noah-typing-dot"></span>
            <span class="noah-typing-dot"></span>
            <span class="noah-typing-dot"></span>
        `;
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTyping() {
        const typingIndicator = document.getElementById('noah-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('noah-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    addWelcomeMessage() {
        setTimeout(() => {
            if (this.messages.length === 0) {
                // Badge notification
                const badge = document.getElementById('noah-badge');
                if (badge) {
                    badge.style.display = 'flex';
                }
            }
        }, 2000);
    }

    // Method to get suggestion for a specific match
    async getMatchSuggestion(teamA, teamB, matchInfo = '') {
        this.openChat();
        this.showTyping();

        try {
            const response = await fetch('/api/groq/suggestion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    team_a: teamA,
                    team_b: teamB,
                    match_info: matchInfo
                })
            });

            if (!response.ok) throw new Error('API Error');

            const data = await response.json();
            this.hideTyping();
            this.addMessage(data.suggestion, 'assistant');

        } catch (error) {
            this.hideTyping();
            this.addMessage(
                `Desculpe, não consegui analisar o jogo ${teamA} vs ${teamB} agora. Tente perguntar sobre estatísticas gerais!`,
                'assistant'
            );
        }
    }

    openChat() {
        if (!this.isOpen) {
            this.toggleChat();
        }
    }
}

// Initialize Noah when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.noah = new NoahAssistant();
});

// Helper function to ask Noah about a specific match
function askNoahAboutMatch(teamA, teamB) {
    if (window.noah) {
        window.noah.openChat();
        window.noah.sendMessage(`Me dê uma análise para o jogo ${teamA} vs ${teamB}`);
    }
}
