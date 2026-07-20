# Estratégia de dados e enriquecimento

## Objetivo

Transformar 6 campos de formulário em contexto suficiente para uma conversa consultiva
com um executivo de segurança — sem depender de bases pagas de enriquecimento.

## Fonte primária: o e-mail corporativo

A landing só aceita e-mail corporativo (domínios gratuitos são bloqueados no frontend e
revalidados no backend). Isso torna o **domínio do e-mail** um identificador confiável da
empresa: `joao@acme.com.br` → site provável `acme.com.br`. O backend deriva
`dominio_empresa` na captação e o scraping parte dele — nenhuma pergunta extra ao lead.

## Pipeline de enriquecimento

```
dominio_empresa
  └─ resolve_website()        https://dominio → https://www.dominio → http://dominio
      └─ scrape_site()        home + /sobre, /quem-somos, /about, /empresa,
          │                   /produtos, /solucoes... (máx. 4 páginas, 12k chars,
          │                   timeout 10s, retry exponencial, User-Agent identificado)
          └─ _extract_text()  título, meta description, h1–h3, parágrafos ≥30 chars,
                              deduplicados (script/style/nav removidos)
  └─ chain de resumo (Claude) → JSON estruturado:
       summary            o que a empresa faz e para quem (2–4 frases)
       industry           setor/segmento
       company_size_hint  indício de porte (relevante p/ ICP 200+)
       ganchos[]          até 3 pontes negócio ↔ segurança/IA para a conversa
```

O resultado é persistido em `lead_enrichment` (conteúdo bruto limitado a 20k chars para
auditoria + campos estruturados) e injetado no system prompt dos agentes como
`contexto_empresa`.

### Princípios

- **Falha não bloqueia o funil.** Site fora do ar, sem conteúdo ou bloqueando bots →
  `lead_enrichment.status='falha'` com o erro registrado, e o engajamento segue com
  contexto vazio (o prompt instrui o agente a operar sem o contexto).
- **Anti-alucinação.** O prompt de resumo proíbe inventar fatos específicos que não
  estejam no texto extraído; campos sem evidência recebem "sem indício claro".
- **Custo controlado.** 1 chamada de LLM por lead no enriquecimento; conteúdo truncado
  em 12k chars; páginas limitadas a 4.
- **Scraping responsável.** User-Agent identificado, timeout curto, sem crawling profundo
  (apenas páginas institucionais previsíveis), uma passada por lead.

## Modelo de dados (Supabase)

Schema aplicado em 3 migrations sequenciais (`database/migrations/000{1,2,3}_*.sql`):
0001 cria o schema base; 0002 adiciona curadoria (`leads.funcionarios`, tipo de
notificação `inscricao_confirmada`, `meetings.tipo`); 0003 adiciona a régua proativa
(`leads.acompanhantes`, tabela `cadence_log`).

| Tabela | Papel | Cardinalidade |
|---|---|---|
| `leads` | Registro captado + estado do funil (`status_lead`, 13 estados) + `funcionarios` (texto livre, 0002) + `acompanhantes` (0–2, 0003) | raiz |
| `lead_enrichment` | Contexto por scraping + resumo do Claude | 1:1 com lead |
| `conversations` | Vínculo negócio↔sessão de memória (fase pré/pós, `session_id` UUID) | 1:N (máx. 2 por lead) |
| `langchain_chat_history` | Memória nativa do LangChain (mensagens JSONB por sessão) | N por conversa |
| `notifications` | Régua de e-mails com agendamento (`unique(lead_id, tipo)` = idempotência) | N por lead |
| `meetings` | Reuniões/eventos no Google Calendar; `tipo` (0002) distingue `reuniao_comercial` de outros usos futuros | N por lead |
| `agent_events` | Auditoria: criação, transições, tool calls, erros | N por lead |
| `cadence_log` | Log da régua proativa anti no-show (0003): 1 linha por toque enviado, `unique(lead_id, touchpoint)` garante idempotência, `respondido` alimenta a lógica de "mudar o ângulo" | N por lead |

Views `vw_funil`, `vw_leads_por_dia` e `vw_leads_por_cargo` servem o dashboard sem
agregações no cliente (o dashboard hoje também calcula métricas derivadas em Python —
probabilidade de presença e temperatura do lead — ver `dashboard/components/scoring.py`).

### Decisões de modelagem

- **`telefone_e164`** é a chave de roteamento do WhatsApp (webhook → lead); o telefone
  original digitado é preservado para exibição.
- **Enums nativos do Postgres** para status/cargo: integridade no banco, não só na aplicação.
- **Memória separada do negócio**: `conversations` guarda *que* conversa existe;
  `langchain_chat_history` guarda *o que* foi dito — e só o LangChain a manipula.
- **Human-in-the-loop fora do banco**: a validação de LinkedIn vive no Google Sheets
  (interface natural para o operador humano); o resultado consolidado (cargo validado,
  URL) é copiado para `leads` pelo agente no momento da qualificação — a planilha é fila
  de trabalho, não fonte de verdade.
- **Idempotência por `unique(lead_id, X)` como padrão repetido**: `notifications`
  (lead_id, tipo) e `cadence_log` (lead_id, touchpoint) usam a mesma técnica — o
  `upsert(..., ignore_duplicates=True)` do Supabase garante que um cron que roda de
  novo (ou dois workers concorrentes) nunca duplica um e-mail ou um toque de WhatsApp.
- **`acompanhantes` como sinal de scoring, não só de logística**: além de reservar
  assentos, a quantidade de acompanhantes informada alimenta a probabilidade de
  presença calculada no dashboard (quem traz alguém tem compromisso social mais forte
  com a própria presença).

## Qualidade e privacidade

- Validações espelhadas frontend/backend (nome composto, e-mail corporativo, telefone,
  cargo em enum) — o backend é a barreira final (`422` na API).
- Deduplicação por `email` único (`409` na captação).
- Dados pessoais mínimos (nome, e-mail, telefone, cargo, empresa); RLS bloqueia acesso
  anônimo; conversas e planilha restritas à operação do evento — base pronta para
  atender LGPD (consentimento coletado na landing, opt-out respeitado pelo agente com
  status `perdido`/motivo `optout`).
