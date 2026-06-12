# Bolão Copa do Mundo 2026

Sistema completo de bolão para a Copa do Mundo 2026 com sistema de pontuação acumulativa, notificações por email e WhatsApp, acompanhamento de placares ao vivo e gerenciamento de premiações.

## Funcionalidades

### Sistema de Pontuação (Lógica Acumulativa)
- **Acertar vencedor/empate:** +2 pontos
- **Acertar gols do Time A:** +2 pontos
- **Acertar gols do Time B:** +2 pontos
- **Bônus placar exato:** +2 pontos
- **Máximo por jogo:** 8 pontos

### Cadastro e Login
- Cadastro com nome, email e WhatsApp
- Verificação de email via código SMTP
- Verificação de WhatsApp via Evolution API
- Autenticação JWT

### Sistema Financeiro
- Inscrição: R$ 100,00
- Por rodada: R$ 10,00
- Prêmio por rodada: R$ 100,00 (distribuição: 50% 1º, 30% 2º, 20% 3º)

### Notificações
- Resultados da rodada por email e WhatsApp
- Notificação aos vencedores
- Lembretes de jogos (1 hora antes)
- Alertas de pagamento pendente

### Administração
- Cadastro de jogos e resultados
- Cálculo automático de rankings
- Confirmação de pagamentos
- Dashboard administrativo

## Tecnologias

- **Backend:** FastAPI (Python)
- **Banco de Dados:** SQLite com SQLAlchemy
- **Frontend:** Bootstrap 5 + JavaScript vanilla
- **Email:** SMTP (Gmail/Outlook/etc)
- **WhatsApp:** Evolution API
- **Autenticação:** JWT

## Instalação

### 1. Clonar/criar o projeto
```bash
cd bolao-copa-2026
```

### 2. Criar ambiente virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 5. Executar aplicação
```bash
python main.py
```

Ou com uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Acessar
- Aplicação: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin: http://localhost:8000/admin

## Configuração

### Email (SMTP)
No arquivo `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
FROM_EMAIL=seu-email@gmail.com
```

Para Gmail, use uma "App Password" em vez da senha normal.

### Evolution API (WhatsApp)
1. Instale a Evolution API: https://github.com/EvolutionAPI/evolution-api
2. Configure no `.env`:
```env
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua-api-key
EVOLUTION_INSTANCE=bolao-copa
```
3. Conecte seu WhatsApp via QR Code no painel da Evolution

## Estrutura do Projeto

```
bolao-copa-2026/
├── app/
│   ├── __init__.py
│   ├── auth.py           # Autenticação JWT
│   ├── database.py       # Configuração DB
│   ├── models.py         # Modelos SQLAlchemy
│   ├── schemas.py        # Schemas Pydantic
│   ├── seed_data.py      # Dados dos jogos
│   ├── routers/          # Endpoints da API
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── matches.py
│   │   ├── predictions.py
│   │   ├── rankings.py
│   │   ├── notifications.py
│   │   └── admin.py
│   └── services/         # Lógica de negócio
│       ├── email_service.py
│       ├── whatsapp_service.py
│       ├── points_calculator.py
│       └── scheduler.py
├── static/
│   ├── css/style.css
│   ├── js/app.js
│   └── templates/        # Templates HTML
│       ├── base.html
│       ├── index.html
│       ├── cadastro.html
│       ├── login.html
│       ├── dashboard.html
│       ├── palpites.html
│       └── ranking.html
├── main.py               # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Primeiros Passos

1. **Criar usuário admin:**
   ```bash
   # Acesse /api/docs e use o endpoint de registro
   # Depois edite no banco para is_admin=true
   ```

2. **Popular jogos:**
   - Acesse como admin
   - Vá em "Admin > Seed Matches"
   - Isso cadastra todos os jogos da Copa 2026

3. **Configurar pagamentos:**
   - Cada usuário precisa pagar R$ 100 de inscrição
   - R$ 10 por rodada que quiser participar

4. **Acompanhar resultados:**
   - Admin atualiza os placares
   - Sistema calcula pontos automaticamente

## API Endpoints

### Auth
- `POST /api/auth/register` - Cadastro
- `POST /api/auth/login` - Login
- `POST /api/auth/verify-email` - Verificar email
- `POST /api/auth/verify-phone` - Verificar WhatsApp
- `GET /api/auth/me` - Perfil do usuário

### Matches
- `GET /api/matches/` - Listar jogos
- `GET /api/matches/live` - Jogos ao vivo
- `GET /api/matches/today` - Jogos de hoje
- `PUT /api/matches/{id}/score` - Atualizar placar (admin)

### Predictions
- `GET /api/predictions/` - Meus palpites
- `POST /api/predictions/` - Fazer palpite
- `GET /api/predictions/{id}/points` - Ver pontos ganhos

### Rankings
- `GET /api/rankings/general` - Ranking geral
- `GET /api/rankings/round/{n}` - Ranking da rodada
- `POST /api/rankings/admin/calculate-round/{n}` - Calcular (admin)

### Admin
- `GET /api/admin/dashboard` - Dashboard stats
- `POST /api/admin/users/{id}/confirm-payment` - Confirmar pagamento
- `POST /api/admin/matches/seed` - Popular jogos

## Contribuição

Projeto open source. Sinta-se livre para contribuir!

## Licença

MIT

---

🏆 **Bolão Copa do Mundo 2026** - Divirta-se e boa sorte!
