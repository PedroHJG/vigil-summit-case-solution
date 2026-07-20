# Réguas de comunicação

Dois canais coordenados: **WhatsApp** (conversacional, conduzido pelo agente LangChain)
e **e-mail** (transacional, conduzido pela régua de notificações). O n8n dispara os
gatilhos; o conteúdo e a decisão de envio são sempre do backend.

## Persona

**Sofia** — SDR virtual do Vigil Summit. Tom humano, consultivo e direto; mensagens
curtas (≤ ~450 caracteres), uma pergunta por vez, no máximo 1 emoji; nunca menciona
ferramentas ou processos internos; respeita opt-out imediatamente.

## Régua WhatsApp — pré-evento (qualificação + curadoria + confirmação)

### Fase 1 — Qualificação e curadoria

| Passo | Gatilho | Conteúdo | Efeito no funil |
|---|---|---|---|
| 1. Boas-vindas | n8n roteia lead novo (≤ ~1 min após inscrição) | Saudação personalizada citando algo real da empresa (contexto do scraping) | `em_conversa` |
| 2. Qualificação | Resposta do lead | Papel de decisão → quantidade de funcionários → principal dor de segurança/IA (uma pergunta por vez) | — |
| 3. Pedido de LinkedIn | Fluxo natural da conversa | Explica a curadoria do convite e pede o link do perfil | — |
| 4. Registro na curadoria | Agente tem LinkedIn + nº de funcionários | Tool `registrar_lead_curadoria` grava a linha na planilha (nome, linkedin, whatsapp, empresa, funcionários, validado=**não**) | `aguardando_validacao` |
| 4b. Fora do perfil | Não-decisor ou empresa < 200 | Encerramento elegante + oferta dos conteúdos gravados (não vai à curadoria) | `desqualificado` |

### Validação humana (Google Sheets)

O curador analisa o LinkedIn, preenche a coluna **cargo** e muda **validado**
para **sim**. O watcher (n8n workflow 04, a cada 2 min →
`POST /internal/validations/run`) detecta e dispara a Fase 2.

Resolução do cargo: planilha > formulário; se a planilha ficou vazia e o
formulário era "Outros", o agente pergunta o cargo na conversa.

### Fase 2 — Reengajamento e confirmação (anti no-show)

| Passo | Gatilho | Conteúdo | Efeito no funil |
|---|---|---|---|
| 5. Reengajamento | Watcher detecta validado=sim | Parabeniza pela vaga aprovada; pergunta o cargo se necessário; reforça o valor do evento com as dores citadas | `qualificado` |
| 6. Botão de confirmação | Lead demonstra intenção | Tool `enviar_botao_confirmacao`: mensagem interativa (botões → lista → texto, conforme o canal aceitar) | — |
| 7. Confirmação | Clique em "✅ Confirmar" (ou "sim" por texto → tool `confirmar_inscricao`) | Backend: e-mail de confirmação (com link opcional "adicionar à agenda") + lembretes D-7/D-1/H-2 agendados; agente comemora. Nenhum evento é criado em agenda nesta etapa | `confirmado` |
| 7b. Recusa | Clique em "Não poderei ir" | Empatia + 1 tentativa de contorno; se mantiver | `perdido` |
| Opt-out | Lead pede para parar (qualquer momento) | Despedida imediata, sem insistência | `perdido` (motivo `optout`) |

## Régua proativa anti no-show (meta: comparecimento > 70%)

Toques de WhatsApp entre a inscrição e o evento, decididos pelo backend
(`cadence_service`) e disparados pelo cron horário do n8n (workflow 05 →
`POST /internal/cadence/run`). **Regras de negócio e racional:**

### Para qualificados que não confirmaram (recuperar a confirmação)

| Toque | Gatilho | Ângulo | Racional |
|---|---|---|---|
| `nudge_confirm_1` | 24h qualificado sem resposta | Prova social ("executivos como você já confirmaram") | 24h respeita a agenda do executivo; repetir o pedido não funciona — mudar o argumento sim |
| `nudge_confirm_2` | 48h após o 1º nudge | Escassez honesta (vagas vão para lista de espera) + botão de novo | Segunda objeção costuma ser prioridade, não interesse |
| `last_call` | D-2 sem confirmação | Última chamada, transparente | Deadline real cria decisão |
| *Expurgo* | 24h após last_call sem resposta | — | `status='perdido'`: libera a vaga e mantém a projeção de presença honesta |

### Para confirmados (reduzir no-show + criar antecipação)

| Toque | Gatilho | Conteúdo | Racional |
|---|---|---|---|
| `companion` | D-7 | Convite para até **2 acompanhantes** (tool `registrar_acompanhantes`) | Quem leva alguém assume compromisso social com a própria presença — o toque mais anti no-show da régua |
| `content` | D-5 | Antecipação personalizada: tema do evento × dor da empresa (do enriquecimento) + pergunta leve | Relevância > lembrete; a resposta é sinal de engajamento |
| `logistics` | D-1 | Logística completa + confirmação dos assentos dos acompanhantes + pedido de OK | O micro-compromisso do "OK" aumenta comparecimento |
| `day_of` | H-3 | Mensagem curtíssima "te esperamos hoje" | Reduz esquecimento no dia sem pedir nada |

### Regras transversais

- **Mensagem adaptativa**: cada toque informa ao agente se o anterior foi
  respondido (`cadence_log.respondido`); se não foi, o agente **muda o ângulo**
  em vez de repetir o argumento.
- **Janela de envio**: 08h–20h (America/Sao_Paulo); fora dela o toque espera o
  próximo ciclo.
- **Frequência**: máximo 1 toque proativo por lead a cada 20h.
- **Idempotência**: `unique(lead_id, touchpoint)` — cada toque sai 1 única vez.
- Qualquer resposta do lead no WhatsApp marca o último toque como respondido
  (feito no webhook, antes do turno do agente).

## Régua de e-mail (notificações)

Enviada pelo cron do n8n (workflow 02, a cada 5 min) via
`POST /internal/notifications/run`. Idempotente por `unique(lead_id, tipo)`.

| Tipo | Agendado em | Momento | Destinatário | Conteúdo |
|---|---|---|---|---|
| `confirmacao_inscricao` | Captação | Imediato | Lead | Recibo: "recebemos sua solicitação"; contato segue no WhatsApp |
| `inscricao_confirmada` | Confirmação (botão) | Imediato | Lead | Vaga garantida + botão "📅 Adicionar à minha agenda" (Google Calendar) |
| `lembrete_d7` | Confirmação | Evento − 7 dias | Lead | Lembrete com data/local |
| `lembrete_d1` | Confirmação | Evento − 1 dia | Lead | Lembrete véspera |
| `lembrete_h2` | Confirmação | Evento − 2 horas | Lead | Última chamada |
| `alerta_interno` | Validação aprovada | Imediato | Time comercial (`SALES_ALERT_EMAIL`) | Ficha completa do lead para abordagem humana se desejado |

Os lembretes anti no-show são agendados **apenas para quem confirmou** — quem
não confirmou é trabalhado pela régua conversacional do WhatsApp, não por
e-mail em massa. Lembretes com horário já passado não são agendados.

## Régua WhatsApp — pós-evento (conversão)

Disparada pelo workflow 03 (diário, 10h) somente após a data do evento, para leads com
status `compareceu`. Nova sessão de memória (fase `pos_evento`), mesmo relacionamento.

| Passo | Conteúdo | Efeito no funil |
|---|---|---|
| 1. Retomada | Agradece a presença + pergunta a impressão do evento | `em_follow_up` |
| 2. Ponte | Conecta um tema do evento à realidade da empresa (contexto enriquecido) | — |
| 3. Proposta | Reunião de 45 min com especialista; 2–3 sugestões de horário comercial | — |
| 4. Agendamento | Lead escolhe → tool `agendar_reuniao` cria a reunião **na agenda do dono** (após rechecar o conflito) e o agente envia dia/hora + **link de lembrete** pedindo que o lead salve na agenda dele (convite por e-mail também é emitido quando o OAuth do dono está ativo) | `reuniao_agendada` |
| 4b. Recusa | Agradece + envia materiais do evento | `perdido` (sem interesse pós-evento) |

## Regras transversais

- **Horário comercial**: reuniões apenas em dias úteis, 9h–18h (BRT), a partir de D+2.
- **Fonte única de decisão**: o n8n nunca escolhe *o que* comunicar — só *quando* chamar
  o backend.
- **Auditoria**: cada mensagem-chave e transição gera `agent_events`; e-mails ficam em
  `notifications` com status (`agendada/enviada/falha`).
- **Falhas de canal**: envios com erro ficam marcados (`falha` + erro) e aparecem no
  dashboard (aba Notificações) para ação manual; o cron não re-tenta automaticamente
  e-mails marcados como falha (decisão explícita para evitar spam em erro sistêmico).
