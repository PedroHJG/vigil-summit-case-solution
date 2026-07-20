# Vigil Summit — Solução de IA ponta a ponta

Solução completa de captação, qualificação e conversão de leads para o evento
**"Vigil Summit — Segurança para a Era da IA"** (executivos CISOs/CTOs de empresas com
200+ funcionários): landing page → enriquecimento por scraping → agente de qualificação
via WhatsApp (LangChain + Claude) → curadoria humana → confirmação de inscrição
(acompanhantes incluídos) → régua proativa anti no-show → follow-up comercial pós-evento
com agendamento real no Google Calendar → dashboard de funil em tempo real.

Case de AI Engineering: agente conversacional com memória persistente, tools tipadas,
human-in-the-loop, orquestração sem lógica de negócio no orquestrador, e métricas de
negócio derivadas (probabilidade de presença, temperatura do lead).

## Sumário

- [Arquitetura](#arquitetura)
- [Fluxo de dados (funil completo)](#fluxo-de-dados-funil-completo)
- [Justificativas de stack](#justificativas-de-stack)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Setup e deploy (local)](#setup-e-deploy-local)
- [Teste ponta a ponta](#teste-ponta-a-ponta)
- [Manipulando `EVENT_DATE` para testes](#manipulando-event_date-para-testes)
- [Troubleshooting](#troubleshooting)
- [Tratamento de erros e rate limits](#tratamento-de-erros-e-rate-limits)
- [Publicando no GitHub](#publicando-no-github)
- [Documentação técnica](#documentação-técnica)

## Arquitetura

```
┌──────────────┐   POST /api/v1/leads    ┌──────────────────────────────────────────┐
│ Landing page │ ──────────────────────► │             Backend FastAPI               │
│ (React/Vite/ │                         │                                            │
│  Three.js)   │                         │  /core      config + cliente Supabase     │
└──────────────┘                         │  /api       contratos Pydantic + rotas    │
┌──────────────┐  polling 30s status=novo│  /services  regras de negócio             │
│     n8n      │◄───────────────────────►│    lead, enrichment, whatsapp, email,     │
│ (roteador,   │  5 workflows:           │    notification, cadence, confirmation,   │
│  sem lógica  │  intake · notifications │    validation                             │
│  de negócio) │  · follow-up · sheets   │  /agent     LangChain (Claude)             │
│              │  watcher · cadence      │    chains.py   pré-evento / pós-evento    │
└──────────────┘  ───────────────────────►    memory.py   PostgresChatMessageHistory │
┌──────────────┐  webhook MESSAGES_      │    prompts.py  Sofia (PT-BR) + régua      │
│ Evolution API│  UPSERT                 │    /tools      scraper·sheets·calendar·  │
│  (WhatsApp)  │◄────────────────────────┤                confirmation·crm           │
└──────▲───────┘                         └────────┬──────────────────┬───────────────┘
       │ sendText / sendButtons                    │                  │
       └────────────────────────────────┌──────────────┐   ┌──────────────────────┐
                                         │   Supabase   │   │ Google Sheets (HITL) │
                                         │ (PostgreSQL) │   │ Google Calendar OAuth│
       ┌──────────────┐  leitura (15s)  │  + memória   │   │ SMTP Gmail (e-mails) │
       │  Streamlit   │◄────────────────│  LangChain   │   └──────────────────────┘
       │  (dashboard) │                 └──────────────┘
       └──────────────┘
```

## Fluxo de dados (funil completo)

1. **Captação** — a landing valida e envia o formulário para `POST /api/v1/leads`; o
   backend revalida (Pydantic), normaliza o telefone para E.164, deriva o domínio
   corporativo do e-mail e insere no Supabase com `status='novo'`. O e-mail de recibo é
   agendado.
2. **Orquestração** — o n8n (workflow **01**) faz polling a cada 30s por leads
   `status='novo'` e roteia: `POST /internal/leads/{id}/enrich` →
   `POST /internal/leads/{id}/engage`.
   _Regra estrita: o n8n não contém lógica de negócio — só detecta gatilhos e chama o
   backend. Toda decisão (o quê enviar, quando qualificar, quando desistir de um lead)
   vive no backend._
3. **Enriquecimento** — o backend resolve o site a partir do domínio do e-mail, faz
   scraping das páginas institucionais (httpx + BeautifulSoup, com retry/timeout) e o
   Claude gera um resumo estruturado (setor, porte, ganchos de conversa) persistido em
   `lead_enrichment`. Falha aqui **não bloqueia o funil**.
4. **Qualificação (pré-evento)** — o agente ("Sofia") inicia a conversa no WhatsApp via
   Evolution API usando o contexto enriquecido: confirma se o lead é decisor, a
   quantidade de funcionários e a principal dor de segurança/IA. Memória 100% do
   LangChain (`PostgresChatMessageHistory` no próprio Supabase).
5. **Curadoria humana (human-in-the-loop)** — o agente pede o LinkedIn e a quantidade de
   funcionários; assim que tem os dois, grava a linha na planilha do Google Sheets
   (tool `registrar_lead_curadoria`) com `validado=não`. Um humano analisa o perfil,
   preenche o **cargo** e muda **validado** para **sim**. O watcher (workflow **04**, a
   cada 2 min) detecta a aprovação e reengaja o lead automaticamente.
6. **Confirmação de inscrição** — a Sofia conduz à confirmação; ao primeiro sinal claro
   de intenção ("sim", "confirmo"), chama a tool `confirmar_inscricao` **na hora** —
   sem esperar clique de botão — e responde com feedback, e pergunta se o lead quer
   levar **até 2 acompanhantes** (tool `registrar_acompanhantes`). Um botão interativo
   do WhatsApp (`sendButtons`, com fallback `sendList` → texto) também é oferecido como
   atalho. E-mail de confirmação + lembretes D-7/D-1/H-2 são agendados nesse momento —
   **não antes** (quem não confirma não recebe spam de lembrete).
7. **Régua proativa anti no-show** — o n8n (workflow **05**, cron horário) chama
   `POST /internal/cadence/run`; o `cadence_service` decide, por regras de negócio
   explícitas, qual toque de WhatsApp enviar a cada lead (recuperação de confirmação,
   convite a acompanhantes, antecipação de conteúdo, logística, lembrete do dia — ver
   [`docs/communication.md`](docs/communication.md)).
8. **Notificações por e-mail** — o n8n (workflow **02**, a cada 5 min) chama
   `POST /internal/notifications/run`; o backend decide e envia recibo, confirmação e
   lembretes + alertas internos ao time comercial.
9. **Pós-evento** — o n8n (workflow **03**, diário às 10h, só após a data do evento)
   chama `POST /internal/follow-ups/run`; o agente abre uma nova sessão de memória
   (fase `pos_evento`), retoma o relacionamento, consulta a disponibilidade **real** da
   agenda do dono (`verificar_disponibilidade`) e agenda a reunião comercial
   (`agendar_reuniao`) com convite ao lead.
10. **Dashboard** — Streamlit lê o Supabase e exibe o funil em tempo real (refresh
    15s), com métricas derivadas: probabilidade de presença por lead, temperatura
    (quente/morno/frio), pessoas esperadas (lead + acompanhantes).

## Justificativas de stack

| Camada              | Escolha                                                        | Por quê                                                                                                                                                                                                      |
| ------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| LLM                 | **Claude (`claude-opus-4-8`)** via `langchain-anthropic`       | Modelo mais capaz da família Opus para conversa consultiva com executivos, tool calling nativo e raciocínio estruturado; configurável por env (`ANTHROPIC_MODEL`) sem mudar código.                          |
| Framework de agente | **LangChain** (`langchain>=0.3,<0.4` — API clássica de agents) | `create_tool_calling_agent` + `AgentExecutor` para tools tipadas, `RunnableWithMessageHistory` + `PostgresChatMessageHistory` para memória nativa persistida no Postgres — sem gerência manual de histórico. |
| Banco               | **Supabase (PostgreSQL)**                                      | Postgres gerenciado com REST imediata (usada pelo polling do n8n), RLS para segurança, e um único banco para negócio + memória do agente.                                                                    |
| Orquestração        | **n8n (Docker local)**                                         | Roteador visual de gatilhos (polling, cron) sem lógica de negócio — trocar/inspecionar fluxos não exige deploy do backend; 5 workflows finos, cada um só dispara um endpoint.                                |
| WhatsApp            | **Evolution API**                                              | API aberta e self-hosted para WhatsApp, com webhook de mensagens, mensagens interativas (botões/listas) e envio de texto.                                                                                    |
| Backend             | **FastAPI (Python)**                                           | Contratos Pydantic compartilhados entre validação e OpenAPI automática; mesma linguagem do ecossistema LangChain.                                                                                            |
| Dashboard           | **Streamlit + Plotly**                                         | Painel analítico em Python puro, com auto-refresh, lendo as mesmas tabelas/views do Supabase; scoring de leads calculado em Python, sem duplicar lógica no banco.                                            |
| E-mail              | **SMTP Gmail (app password)**                                  | Reusa a conta Google já necessária p/ Sheets/Calendar; `EMAIL_MOCK_MODE=true` permite demo completa sem credenciais de e-mail.                                                                               |
| Frontend 3D         | **Three.js + GSAP**                                            | Cadeado 3D (modelo comprimido com Draco, ~1,4 MB) e campo de partículas na landing; loop de render pausado fora da viewport (IntersectionObserver) para não gastar CPU/GPU com a seção fora da tela.         |

## Estrutura de pastas

```
/case-ai-engineer-pareto
├── Landing page VIGIL SUMMIT/     # React + Vite + Tailwind + Three.js + GSAP
│   └── src/components/landing/    # seções da página + 3d/ (Lock3D, ParticleOrb) + particles/
├── backend/                       # FastAPI + LangChain
│   ├── main.py
│   ├── restart.ps1                # mata o processo da porta 8000 e sobe de novo
│   ├── core/                      # config (Settings via pydantic-settings) + cliente Supabase
│   ├── api/                       # rotas (leads, internal, webhooks) + schemas Pydantic
│   ├── agent/                     # chains, memory, prompts (Sofia + régua) + tools/
│   │   └── tools/                 # scraper, sheets, calendar, confirmation, crm
│   ├── services/                  # lead, enrichment, whatsapp, email, notification,
│   │                               # cadence, confirmation, validation, agent_service
│   ├── scripts/                   # chat_local.py, google_oauth_setup.py
│   └── credentials/                # service_account.json, oauth_client.json (git-ignored)
├── database/migrations/           # 0001_init · 0002_curadoria_confirmacao · 0003_acompanhantes_cadencia
├── n8n-evolution/                 # docker-compose (n8n + Evolution API + Postgres + Redis)
│   └── workflows/                 # 5 workflows JSON prontos para importar no n8n
├── dashboard/                     # Streamlit
│   └── components/                # data.py (Supabase), scoring.py (prob./temperatura),
│                                   # dash_charts.py (Plotly), theme.py (paleta dark)
└── docs/
    ├── architecture.md            # desenho da solução, fluxo do LangChain, decisões
    ├── data_strategy.md           # enriquecimento e modelo de dados
    ├── communication.md           # réguas de comunicação (WhatsApp + e-mail)
    └── testing.md                 # como simular o tempo (EVENT_DATE) e diagnosticar problemas
```

## Setup e deploy (local)

### 0. Pré-requisitos

Python 3.11+, Node 18+, Docker Desktop, uma conta Supabase, uma chave Anthropic, um
número de WhatsApp para conectar na Evolution e um projeto Google Cloud (Sheets +
Calendar).

### 1. Supabase

1. Crie um projeto em [supabase.com](https://supabase.com).
2. SQL Editor → cole e execute, **nesta ordem**, os 3 arquivos de
   `database/migrations/`: `0001_init.sql`, `0002_curadoria_confirmacao.sql`,
   `0003_acompanhantes_cadencia.sql`.
3. Anote: `SUPABASE_URL`, a chave `service_role` e a connection string
   (Connect → Session pooler) para `DATABASE_URL`.

### 2. Google (Sheets + Calendar)

1. No Google Cloud Console: crie um projeto, habilite **Google Sheets API** e
   **Google Calendar API**, crie uma **service account** e baixe o JSON da chave em
   `backend/credentials/service_account.json`.
2. Crie a planilha de curadoria com o cabeçalho (linha 1):
   `nome | link do linkedin | whatsapp | cargo | empresa | quantidade de funcionários na empresa | validado`
   e **compartilhe com o e-mail da service account como Editor**. O matching das
   colunas é por palavra-chave, então variações de texto no cabeçalho funcionam. Anote
   o ID da planilha (trecho da URL entre `/d/` e `/edit`).
   - O **agente** preenche: nome, linkedin, whatsapp, empresa, funcionários e
     validado="não".
   - O **humano** preenche: **cargo** (analisado no LinkedIn) e muda **validado** para
     "sim" — isso dispara o reengajamento automático (workflow 04).
3. **Calendar — use OAuth do dono da agenda (recomendado):**
   1. No mesmo projeto: Credentials → Create Credentials → OAuth client ID (tipo
      **Desktop app**) → baixe o JSON em `backend/credentials/oauth_client.json` (na
      tela de consentimento, adicione seu e-mail como _test user_).
   2. Rode `python -m scripts.google_oauth_setup` (a partir de `/backend`) e autorize
      com a conta dona da agenda no navegador que abrir.

   O Calendar é usado **somente para a reunião comercial pós-evento**: ela entra na
   agenda do dono e o lead recebe convite por e-mail + link de lembrete no WhatsApp. A
   tool `verificar_disponibilidade` consulta o free/busy real antes de propor
   horários. A confirmação de inscrição no evento **não** cria eventos em agenda
   (apenas e-mail + lembretes).

   > ⚠️ **Enquanto o app OAuth estiver em modo "Testing"** na tela de consentimento do
   > Google Cloud, o token expira em **7 dias** e precisa ser renovado rodando o
   > script de novo (ver [`docs/testing.md`](docs/testing.md#o-agente-parou-de-responder-no-meio-de-uma-conversa)).
   > Publique o app em "Production" para eliminar essa manutenção — não exige
   > verificação do Google para uso próprio com o escopo `calendar`.

   _Fallback (só service account, sem OAuth)_: compartilhe a agenda do dono com o
   e-mail da service account (permissão "fazer alterações") e coloque o e-mail do dono
   em `GOOGLE_CALENDAR_ID`. O Google bloqueia o convite automático ao lead nesse modo
   (ele recebe só o link "adicionar à agenda" por e-mail/WhatsApp).

### 3. Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # preencha as credenciais anotadas acima
uvicorn main:app --host 0.0.0.0 --port 8000
```

Swagger em `http://localhost:8000/docs`. Depois de qualquer alteração no `.env`, use
`.\restart.ps1` (PowerShell) para reiniciar — a config é lida só no startup.

`EMAIL_MOCK_MODE=true` permite rodar a demo completa sem credenciais SMTP: os e-mails
são apenas logados em vez de enviados.

### 4. n8n + Evolution API

O `docker-compose.yml` sobe 5 containers na rede `evolution-net`: `evolution_api`
(porta **8080**, imagem `evoapicloud/evolution-api`), `evolution_frontend` (manager web,
porta **3000**), `evolution_postgres` e `evolution_redis` (infra interna da Evolution,
não expostos), e `vigil-n8n` (porta **5678**).

```bash
cd n8n-evolution
copy .env.example .env      # preencha (ver comentários no arquivo)
docker compose up -d
```

1. **Evolution** (`http://localhost:8080/manager` ou `http://localhost:3000`): crie a
   instância `vigil`, leia o QR code com o WhatsApp que vai representar a Sofia.
   Configure o webhook da instância para
   `http://host.docker.internal:8000/api/v1/webhooks/evolution` com o evento
   `MESSAGES_UPSERT`.
2. **n8n** (`http://localhost:5678`): crie a conta local e importe os **5** JSONs de
   `n8n-evolution/workflows/`. Ative todos exceto o `03-post-event-followup` até você
   estar pronto para testar o pós-evento (ele roda diariamente às 10h e só age depois
   da data real/simulada do evento):
   - `01-lead-intake-router` — polling de leads novos (30s) → enrich → engage.
   - `02-notifications-cron` — e-mails vencidos (5 min).
   - `04-validation-watcher` — checa a planilha de curadoria (2 min).
   - `05-cadence-cron` — régua proativa anti no-show (1h).
   - `03-post-event-followup` — follow-up comercial (diário, 10h).

### 5. Landing page

```bash
cd "Landing page VIGIL SUMMIT"
npm i && npm run dev            # http://localhost:5173
```

O dev server é exposto na rede local (`server.host: true`) — dá para abrir do celular
em `http://SEU_IP_LOCAL:5173` para testar o formulário em mobile (ver
[Troubleshooting](#troubleshooting)). O formulário envia para
`http://${window.location.hostname}:8000` por padrão (mesmo host que serviu a página);
defina `VITE_API_URL` no `.env` da landing só se o backend estiver em outro endereço.

### 6. Dashboard

```bash
cd dashboard
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py            # http://localhost:8501
```

## Teste ponta a ponta

1. Preencha o formulário na landing (e-mail corporativo + o SEU WhatsApp).
2. Em até ~30s o n8n roteia enriquecimento + engajamento e a Sofia chama no WhatsApp.
3. Responda às perguntas de qualificação; envie um LinkedIn e a quantidade de
   funcionários — o lead vai para `aguardando_validacao` e ganha uma linha na planilha
   de curadoria.
4. Na planilha: preencha **cargo** e mude **validado** para **sim**. Em até 2 min
   (workflow 04) a Sofia retoma a conversa, parabenizando pela aprovação.
5. Confirme por texto ("sim, pode confirmar") ou pelo botão interativo — a Sofia
   responde com feedback e pergunta sobre acompanhantes (0 a 2).
6. Acompanhe o funil, a temperatura dos leads e a projeção de pessoas esperadas no
   dashboard.
7. Para ver a régua proativa e o pós-evento sem esperar dias reais passarem, siga
   [`docs/testing.md`](docs/testing.md).

> Sem WhatsApp/Google configurados, teste o agente no terminal:
> `python -m scripts.chat_local <lead_id>` (usa a mesma chain e memória do fluxo real).

## Manipulando `EVENT_DATE` para testes

Toda a régua de tempo (anti no-show, lembretes, liberação do pós-evento) compara a hora
real de agora com `EVENT_DATE` (`backend/.env`) — **é essa variável que se manipula
para simular o tempo passando**, nunca a data do sistema operacional (quebraria
TLS/OAuth/Docker). Resumo rápido:

| Cenário                             | Ajuste                                                        |
| ----------------------------------- | ------------------------------------------------------------- |
| Toque `companion` (D-7)             | `EVENT_DATE` = hoje + 6 dias                                  |
| Toque `logistics` (D-1)             | `EVENT_DATE` = amanhã                                         |
| Pós-evento / agendamento de reunião | `EVENT_DATE` = ontem + `UPDATE leads SET status='compareceu'` |

Depois de editar, **sempre reinicie o backend** (`.\restart.ps1`). O guia completo —
todos os 7 toques da régua, como resetar `cadence_log`/`notifications` entre testes, e
como simular o follow-up pós-evento — está em **[`docs/testing.md`](docs/testing.md)**.

## Troubleshooting

Problemas mais comuns ao rodar localmente (guia completo com comandos em
[`docs/testing.md`](docs/testing.md)):

- **"O agente parou de responder"** → quase sempre o token OAuth do Google Calendar
  expirou (7 dias em modo Testing) e uma tool falhou silenciosamente. Renove com
  `python -m scripts.google_oauth_setup`.
- **Formulário não envia pelo celular** → confira se `VITE_API_URL` não está
  sobrescrevendo o fallback automático, e libere a porta 8000 no Firewall do Windows
  (regra por porta, não basta liberar `python.exe` — o `.venv` do projeto é um
  executável diferente do Python do sistema).
- **"Porta já em uso"** ao subir backend/dashboard → processo órfão de uma sessão
  anterior; `.\restart.ps1` resolve para o backend, ou mate manualmente via
  `Get-NetTCPConnection -LocalPort 8000 -State Listen`.

## Tratamento de erros e rate limits

- **Anthropic**: `max_retries=3` no `ChatAnthropic` (backoff exponencial do SDK em
  429/5xx).
- **Evolution API**: `tenacity` com backoff exponencial em 429/5xx/timeout (4
  tentativas); confirmação de inscrição tenta `sendButtons` → `sendList` → texto puro,
  na ordem, conforme o canal aceitar.
- **Google Sheets**: retry exponencial em `APIError` (cota de 60 leituras/min);
  indisponibilidade retorna erro amigável para o agente adiar a verificação.
- **Google Calendar**: retry em 429/5xx; fallback sem `attendees` quando a credencial
  não pode convidar participantes; `GoogleAuthError` (token expirado/revogado) é
  capturada explicitamente e nunca derruba o turno — vira uma mensagem de erro tratada
  para a tool, e não uma exceção que sobe até o webhook.
- **Rede de segurança do agente**: se qualquer tool ou o LLM falhar de um jeito
  imprevisto, `agent_service` garante que o lead recebe uma mensagem de desculpas em
  vez de silêncio — uma falha interna nunca deve parecer "o agente travou" pelo lado
  de fora.
- **Scraping**: timeout de 10s, máx. 4 páginas, retry em erro de transporte; falha
  **não** bloqueia o funil (lead segue sem contexto, erro registrado em
  `lead_enrichment`).
- **Webhook Evolution**: responde sempre 200 (evita re-entrega em loop); eventos
  irrelevantes são ignorados de forma barata.
- **Polling n8n**: o backend muda o lead para `enriquecendo` na primeira chamada (lock
  otimista), evitando reprocessamento no ciclo seguinte.
- **Régua proativa**: idempotente por `unique(lead_id, touchpoint)`; janela de envio
  08h–20h; máximo 1 toque por lead a cada 20h; expurga (`status='perdido'`) leads que
  não respondem 24h após a última chamada, liberando a vaga.

## Documentação técnica

- [`docs/architecture.md`](docs/architecture.md) — desenho da solução, fluxo do
  LangChain (chains, tools, memória, ciclo de um turno), decisões e trade-offs.
- [`docs/data_strategy.md`](docs/data_strategy.md) — estratégia de enriquecimento e
  modelo de dados completo (8 tabelas, 3 migrations).
- [`docs/communication.md`](docs/communication.md) — réguas de comunicação completas:
  WhatsApp pré-evento (qualificação, curadoria, confirmação), régua proativa anti
  no-show (7 toques com racional de negócio), e-mail e pós-evento.
- [`docs/testing.md`](docs/testing.md) — como manipular `EVENT_DATE` para testar cada
  toque da régua sem esperar dias reais, e diagnóstico dos problemas mais comuns do
  ambiente local.
