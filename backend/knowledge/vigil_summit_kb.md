# Base de Conhecimento — Vigil Summit: Segurança para a Era da IA

> Este documento é a fonte de verdade (knowledge base) para o agente de IA da Vigil.AI.
> Cada seção abaixo (nível `##`) foi escrita como um \\\*\\\*chunk autocontido\\\*\\\*: pode ser
> indexada individualmente em um vector store (embeddings) sem perder contexto, permitindo
> que o agente recupere só a parte relevante para responder ou personalizar uma mensagem.
> Metadados sugeridos de chunking (`tags`) estão no fim de cada seção — use-os como
> metadata no seu banco vetorial (ex.: Pinecone, pgvector, Weaviate) para filtrar buscas
> por fase do funil.

\---

## 1\. Visão Geral do Evento

O **Vigil Summit — Segurança para a Era da IA** é o evento corporativo anual da Vigil.AI,
plataforma SaaS de monitoramento contínuo de postura de segurança cibernética. O evento é
**presencial, exclusivo e por convite/inscrição aprovada**, com capacidade para **120
participantes**.

* **Formato:** presencial, dia único, das 9h às 18h.
* **Data:** 20 de agosto de 2026
* **Local:** Hotel Hyatt, São Paulo
* **Capacidade:** 120 lugares (inscrição sujeita a aprovação por perfil).
* **Objetivo do evento:** não é apenas educacional — é comercial. A meta é sair do evento
com o maior número possível de reuniões comerciais agendadas com decisores que
assistiram às sessões e viram a demo da plataforma.
* **Formato do dia:** 1 keynote de abertura, 1 sessão técnica aprofundada, 1 painel com
demonstração ao vivo, coffee breaks para networking, e um "Vigil Lounge" para
agendamento de reuniões 1:1 com o time comercial ao final do dia.

`tags: overview, evento, logistica, data, local`

\---

## 2\. Público-Alvo (Perfil do Convidado)

O Vigil Summit é desenhado para **decisores técnicos e de risco** em empresas de médio e
grande porte:

* **Cargos-alvo:** CISOs, CTOs, Diretores de TI, Heads de Segurança da Informação,
Gestores de Risco e Compliance.
* **Porte da empresa:** acima de 200 funcionários.
* **Dor principal que os traz ao evento:** dificuldade de manter visibilidade contínua
sobre a postura de segurança, fadiga de alertas, e pressão de compliance (LGPD, ISO
27001, SOC 2) sem aumentar o time.
* **O que o agente deve inferir no enriquecimento:** se o lead trabalha em setor regulado
(financeiro, saúde, governo), isso é um forte gatilho de interesse na Sessão 3
(Conformidade). Se o lead é mais técnico (ex.: cargo com "Engineering", "SOC",
"Threat"), o gatilho é a Sessão 2 (Machine Learning).

`tags: overview, publico-alvo, icp, personas`

\---

## 3\. Conteúdo Programático

### 3.1 Sessão 1 — Keynote de Abertura: "A Evolução da Segurança Reativa para a Defesa Ativa"

* **Formato:** Keynote, palco principal, 45 minutos + 10 min de Q\&A.
* **Horário sugerido:** 9h30 (abertura do evento).
* **Tema central:** a transição de modelos de segurança reativos (responder após o
incidente) para modelos de **defesa ativa**, nos quais a infraestrutura antecipa e
neutraliza ameaças autônomas geradas por IA antes que causem dano.
* **O que o participante vai aprender:**

  * Por que ameaças autônomas (ataques orquestrados ou executados por agentes de IA)
mudam o cálculo de risco tradicional.
  * Quais os pilares de uma arquitetura de defesa ativa (visibilidade contínua, resposta
automatizada, priorização inteligente de risco).
  * Como preparar a infraestrutura de segurança da empresa para essa nova era.
* **Para quem é mais relevante:** decisores estratégicos (CISO, CTO, Diretor de TI) que
precisam justificar investimento e mudança de postura para a liderança.
* **Gancho para follow-up comercial:** leads que interagem/perguntam nesta sessão
demonstram preocupação estratégica de longo prazo — a mensagem pós-evento pode
conectar a keynote com uma demo do módulo de priorização de risco da plataforma.
* **Palavras-chave para retrieval:** defesa ativa, segurança reativa, ameaças autônomas,
IA ofensiva, infraestrutura de segurança, keynote de abertura.

`tags: programa, sessao-1, keynote, estrategico, tags-retrieval:defesa-ativa`

\---

### 3.2 Sessão 2 — Sessão Técnica: "Machine Learning contra a Fadiga de Alertas"

* **Formato:** Sessão técnica aprofundada (deep dive), 40 minutos + 15 min de Q\&A técnico.
* **Horário sugerido:** 11h (após coffee break).
* **Tema central:** como o motor de Machine Learning da Vigil.AI processa milhões de logs
de segurança em tempo real, eliminando a fadiga de alertas (alert fatigue) e priorizando
apenas os riscos reais que exigem ação humana.
* **O que o participante vai aprender:**

  * Como funciona a análise de logs em escala (milhões de eventos/dia) sem gargalo
humano.
  * A lógica de priorização de risco: como o modelo distingue ruído de sinal.
  * Casos práticos de redução de tempo de resposta (MTTR) com priorização automatizada.
* **Para quem é mais relevante:** perfis técnicos (SOC Managers, Engenheiros de
Segurança, Analistas de Threat Intelligence) e CTOs preocupados com eficiência
operacional do time.
* **Gancho para follow-up comercial:** leads técnicos costumam querer ver a plataforma
"por dentro" — o follow-up pode oferecer uma demo técnica hands-on ou trial sandbox,
em vez de uma reunião puramente comercial.
* **Palavras-chave para retrieval:** machine learning, fadiga de alertas, priorização de
riscos, análise de logs em tempo real, MTTR, SOC, motor de ML.

`tags: programa, sessao-2, tecnica, ml, tags-retrieval:fadiga-de-alertas`

\---

### 3.3 Sessão 3 — Painel + Demo ao Vivo: "Conformidade sem Burocracia"

* **Formato:** Painel de discussão seguido de demonstração ao vivo do produto, 50 minutos
(25 min painel + 25 min demo).
* **Horário sugerido:** 14h (após almoço).
* **Tema central:** como automatizar a coleta de evidências e a geração de relatórios de
conformidade para **ISO 27001, LGPD e SOC 2**, eliminando o trabalho manual e repetitivo
de auditoria.
* **O que o participante vai ver ao vivo:**

  * Demonstração real da plataforma coletando evidências automaticamente.
  * Geração de um relatório de conformidade completo em minutos, ao vivo, no palco.
  * Painel com especialistas discutindo os principais desafios de compliance em empresas
reguladas.
* **Para quem é mais relevante:** Gestores de Risco e Compliance, Diretores de TI em
setores regulados (financeiro, saúde, governo), e qualquer decisor cuja empresa já
sofreu com auditorias demoradas.
* **Gancho para follow-up comercial:** esta é a sessão com **maior potencial de conversão
direta** — quem assiste a uma demo ao vivo de geração de relatório já viu valor
tangível. O follow-up deve referenciar especificamente o framework de compliance
relevante para o setor do lead (ex.: "vi que vocês são do setor financeiro — nosso
módulo de evidências para SOC 2 pode encaixar direto no seu ciclo de auditoria").
* **Palavras-chave para retrieval:** conformidade, compliance, ISO 27001, LGPD, SOC 2,
automação de evidências, relatórios de auditoria, painel, demo ao vivo.

`tags: programa, sessao-3, compliance, demo, tags-retrieval:iso27001-lgpd-soc2`

\---

## 4\. Agenda Consolidada (linha do tempo)

|Horário|Atividade|
|-|-|
|09h00|Credenciamento e welcome coffee|
|09h30|Sessão 1 — Keynote: Defesa Ativa|
|10h15|Networking / Coffee break|
|11h00|Sessão 2 — Técnica: ML contra Fadiga de Alertas|
|12h00|Almoço|
|14h00|Sessão 3 — Painel + Demo: Conformidade sem Burocracia|
|15h00|Vigil Lounge — agendamento de reuniões comerciais 1:1|
|17h00|Encerramento e networking final|

`tags: programa, agenda, cronograma`

\---

## 5\. Perguntas Frequentes (FAQ para o agente)

**O evento tem custo?**
mediante aprovação de inscrição por perfil

**Posso levar acompanhante?**
sim, mediante confirmação prévia

**Haverá gravação/conteúdo disponível depois?**
Não haverá gravação do evento

**As sessões têm certificado ou material para download?**
sim, haverá material para download durante o evento

`tags: faq, logistica, engajamento`

\---

## 6\. Guia de Uso para o Agente de IA

Este documento deve ser consumido pelo agente principalmente em três momentos do funil:

1. **Fase 3 — Engajamento pré-evento:** usar as seções 3.1–3.3 para gerar mensagens de
antecipação personalizadas conforme o interesse detectado no enriquecimento do lead
(ex.: lead de setor financeiro → destacar Sessão 3; lead com cargo técnico → destacar
Sessão 2).
2. **Fase 4 — Follow-up pós-evento:** usar o campo "Gancho para follow-up comercial" de
cada sessão para redigir a mensagem de agendamento de reunião, referenciando
especificamente o que o lead assistiu ou demonstrou interesse.
3. **Respostas a dúvidas do lead:** usar a seção 4 (FAQ) para responder perguntas
recorrentes sem intervenção humana.

**Recomendação de chunking para embeddings:** indexe cada seção `##`/`###` como um
documento separado, com os `tags` como metadata. Isso permite que o agente recupere,
por exemplo, apenas a Sessão 3 quando o lead pergunta sobre "conformidade" ou "LGPD",
sem trazer contexto irrelevante das outras sessões.

`tags: meta, instrucoes-agente, rag-strategy`

