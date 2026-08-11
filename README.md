# 💎 FINA — Assistente Financeiro Pessoal com IA

> Gerencie suas finanças por voz ou chat, conecte cartões via Open Finance Brasil e receba orientações inteligentes da FINA.

---

## 🏗️ Arquitetura

```
📱 Flutter App (iOS + Android)
        ↕ HTTPS / JWT
🖥️  FastAPI Backend (Python 3.12)
        ↕
🗄️  PostgreSQL 16          — dados dos usuários (criptografados)
⚡  Redis 7                — cache e rate limiting
🤖  Anthropic Claude API   — IA conversacional
🏦  Pluggy Open Finance    — conexão bancária somente leitura
```

---

## 📁 Estrutura do Projeto

```
fina/
├── backend/                    ← API Python (FastAPI)
│   ├── app/
│   │   ├── main.py             ← Entry point
│   │   ├── core/
│   │   │   ├── config.py       ← Configurações (env vars)
│   │   │   ├── database.py     ← SQLAlchemy async
│   │   │   └── security.py     ← JWT + criptografia
│   │   ├── models/
│   │   │   └── models.py       ← Tabelas do banco
│   │   ├── schemas/
│   │   │   └── schemas.py      ← Pydantic validação
│   │   ├── api/
│   │   │   ├── auth.py         ← Login/registro/refresh
│   │   │   ├── transactions.py ← Receitas e despesas
│   │   │   ├── cards.py        ← Cartões + Open Finance
│   │   │   ├── goals.py        ← Metas financeiras
│   │   │   ├── ai_chat.py      ← Chat com Claude
│   │   │   └── reports.py      ← Score e relatórios
│   │   └── services/
│   │       ├── user_service.py         ← CRUD usuários
│   │       └── openfinance_service.py  ← Integração Pluggy
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── flutter_app/                ← App móvel (iOS + Android)
│   ├── lib/
│   │   ├── main.dart           ← Entry point
│   │   ├── core/theme/         ← Tema visual
│   │   ├── services/
│   │   │   └── api_service.dart ← HTTP client (Dio)
│   │   ├── screens/
│   │   │   ├── chat_screen.dart      ← Chat + voz
│   │   │   ├── dashboard_screen.dart ← Gráficos e métricas
│   │   │   └── app_router.dart       ← Navegação + login
│   │   └── router/
│   │       └── app_router.dart
│   └── pubspec.yaml
│
├── .github/workflows/
│   └── deploy.yml              ← CI/CD completo
├── docker-compose.yml          ← Dev local completo
└── railway.toml                ← Deploy Railway
```

---

## 🚀 Rodando Localmente

### Pré-requisitos
- Python 3.12+
- Docker e Docker Compose
- Flutter 3.24+
- Conta Anthropic (para API key)

### 1. Backend

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/fina.git
cd fina

# Suba o banco de dados e Redis
docker compose up postgres redis -d

# Configure as variáveis de ambiente
cp backend/.env.example backend/.env
# Edite backend/.env com suas chaves

# Instale as dependências
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Inicie a API
uvicorn app.main:app --reload --port 8000
```

A API estará em: http://localhost:8000
Documentação interativa: http://localhost:8000/docs

### 2. App Flutter

```bash
cd flutter_app

# Instale as dependências
flutter pub get

# Configure a URL da API (em lib/services/api_service.dart)
# const _baseUrl = 'http://10.0.2.2:8000/api/v1';  # Android emulator
# const _baseUrl = 'http://localhost:8000/api/v1';  # iOS simulator

# Rode no emulador/dispositivo
flutter run
```

---

## ☁️ Deploy em Produção

### Backend — Railway (recomendado)

1. Crie conta em [railway.app](https://railway.app)
2. Crie um projeto com os serviços: **API**, **PostgreSQL**, **Redis**
3. Configure as variáveis de ambiente no painel
4. Conecte seu repositório GitHub — o deploy é automático

```bash
# Ou via CLI
npm install -g @railway/cli
railway login
railway up
```

### App — Google Play Store

1. Gere o keystore:
```bash
keytool -genkey -v -keystore fina-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias fina
```

2. Configure `flutter_app/android/key.properties`
3. Build e upload:
```bash
cd flutter_app
flutter build appbundle --release
# Faça upload do .aab no Google Play Console
```

### App — Apple App Store

1. Configure o Bundle ID `br.com.fina.app` no Xcode
2. Adicione certificado de distribuição no Apple Developer
3. Build e upload via Xcode ou CI/CD:
```bash
cd flutter_app
flutter build ipa --release
# Upload via Xcode Organizer ou xcrun altool
```

---

## 🔐 Segurança Implementada

| Recurso | Implementação |
|---|---|
| Senhas | bcrypt (salt automático) |
| Sessões | JWT + Refresh Token rotation |
| Dados bancários | Fernet AES-128 no banco |
| HTTPS | Obrigatório em produção |
| CORS | Origens restritas |
| Rate limiting | Redis (via middleware) |
| Open Finance | Somente leitura, revogável |

---

## 🏦 Open Finance Brasil

A integração usa a **Pluggy** como agregador homologado pelo Banco Central.

**Bancos suportados:** Nubank, Itaú, Bradesco, Santander, BB, Caixa, Inter, C6, e outros +200.

**Como funciona:**
1. Usuário toca "Conectar banco" no app
2. App busca `connect_token` da API (`GET /api/v1/cards/openfinance/connect-token`)
3. Widget Pluggy abre fluxo OAuth com o banco
4. Após autorização, `item_id` e `account_id` são enviados à API
5. API sincroniza limite, fatura e transações automaticamente

**Privacidade:** acesso é somente leitura e pode ser revogado a qualquer momento.

---

## 🤖 Funcionalidades de IA

A FINA usa Claude Sonnet com contexto financeiro real do usuário:

- **Análise de saúde financeira** — score 0–100 com alertas
- **Orientação de compras** — "Posso comprar X agora?"
- **Projeções** — "Em quanto tempo junto R$5.000?"
- **Padrões de gastos** — identifica categorias problemáticas
- **Voz** — entrada por microfone + resposta em voz
- **Histórico** — conversa salva no banco, contexto persistente

---

## 📦 Tecnologias

| Camada | Tecnologia |
|---|---|
| API | FastAPI 0.115 + Python 3.12 |
| Banco | PostgreSQL 16 + SQLAlchemy async |
| Cache | Redis 7 |
| IA | Anthropic Claude Sonnet |
| Open Finance | Pluggy API |
| App móvel | Flutter 3.24 + Dart 3 |
| HTTP Client | Dio + Interceptors |
| Estado | Riverpod |
| Navegação | GoRouter |
| Gráficos | fl_chart |
| Voz | speech_to_text + flutter_tts |
| CI/CD | GitHub Actions |
| Deploy | Railway + Docker |

---

## 📋 Próximos Passos

- [ ] Push notifications (alertas de gastos)
- [ ] Widget na tela inicial do celular
- [ ] Importação de extratos PDF/OFX
- [ ] Modo planejamento orçamentário (50/30/20)
- [ ] Relatórios em PDF
- [ ] Integração com carteiras de investimento
- [ ] Modo offline com sincronização

---

## 📄 Licença

MIT © FINA — Assistente Financeiro Pessoal