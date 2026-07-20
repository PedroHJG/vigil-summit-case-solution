-- ============================================================================
-- Vigil Summit — Modelo de dados (Supabase / PostgreSQL)
-- Migration 0001: schema inicial
--
-- Como aplicar:
--   Opção A) Supabase Dashboard > SQL Editor > colar e executar este arquivo
--   Opção B) supabase db push (via Supabase CLI, com este arquivo em
--            supabase/migrations/)
--
-- O backend acessa o banco com a SERVICE_ROLE key (bypassa RLS).
-- RLS fica habilitado sem policies => acesso anônimo bloqueado por padrão.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------------------
-- Enums
-- ----------------------------------------------------------------------------

-- Cargos exatamente como capturados pelo formulário da landing page
do $$ begin
  create type cargo_lead as enum (
    'CTO', 'CISO', 'Diretor de TI', 'Gestor de Risco', 'Outros'
  );
exception when duplicate_object then null; end $$;

-- Funil completo do lead (pré-evento -> evento -> pós-evento)
do $$ begin
  create type status_lead as enum (
    'novo',                   -- inserido pela landing, aguardando orquestração
    'enriquecendo',           -- scraping em andamento (lock do polling n8n)
    'enriquecido',            -- contexto da empresa capturado
    'em_conversa',            -- agente iniciou qualificação via WhatsApp
    'aguardando_validacao',   -- LinkedIn enviado; aguarda validação humana (Sheets)
    'qualificado',            -- validado + perfil aderente (ICP)
    'desqualificado',         -- fora do perfil (ex.: empresa < 200 funcionários)
    'confirmado',             -- presença confirmada no evento
    'compareceu',             -- fez check-in no evento
    'ausente',                -- confirmado mas não compareceu
    'em_follow_up',           -- agente retomou contato pós-evento
    'reuniao_agendada',       -- reunião comercial criada no Google Calendar
    'perdido'                 -- sem resposta / optout
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type fase_conversa as enum ('pre_evento', 'pos_evento');
exception when duplicate_object then null; end $$;

do $$ begin
  create type status_conversa as enum ('ativa', 'encerrada', 'pausada');
exception when duplicate_object then null; end $$;

do $$ begin
  create type status_enriquecimento as enum ('pendente', 'sucesso', 'falha');
exception when duplicate_object then null; end $$;

do $$ begin
  create type tipo_notificacao as enum (
    'confirmacao_inscricao',  -- e-mail imediato pós-cadastro
    'lembrete_d7',            -- 7 dias antes do evento
    'lembrete_d1',            -- 1 dia antes do evento
    'lembrete_h2',            -- 2 horas antes do evento
    'alerta_interno'          -- alerta ao time comercial (lead qualificado etc.)
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type status_notificacao as enum ('agendada', 'enviada', 'falha', 'cancelada');
exception when duplicate_object then null; end $$;

do $$ begin
  create type status_reuniao as enum ('agendada', 'realizada', 'cancelada');
exception when duplicate_object then null; end $$;

-- ----------------------------------------------------------------------------
-- Função utilitária: updated_at automático
-- ----------------------------------------------------------------------------

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ----------------------------------------------------------------------------
-- leads — registro captado pela landing page
-- ----------------------------------------------------------------------------

create table if not exists leads (
  id               uuid primary key default gen_random_uuid(),
  nome             text not null,
  email            text not null unique,
  ddi              text not null default '+55',
  telefone         text not null,            -- como digitado: "(11) 9 9999-9999"
  telefone_e164    text not null,            -- normalizado: "+5511999999999" (chave p/ WhatsApp)
  cargo            cargo_lead not null,
  empresa          text not null,
  dominio_empresa  text,                     -- derivado do e-mail corporativo (base do scraping)
  status           status_lead not null default 'novo',
  linkedin_url     text,                     -- informado pelo lead na conversa
  cargo_validado   text,                     -- preenchido pelo humano no Google Sheets
  lead_score       int,                      -- 0-100, atribuído pelo agente na qualificação
  motivo_status    text,                     -- justificativa da última transição (auditoria)
  origem           text not null default 'landing_page',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists idx_leads_status on leads (status);
create index if not exists idx_leads_telefone_e164 on leads (telefone_e164);
create index if not exists idx_leads_created_at on leads (created_at desc);

drop trigger if exists trg_leads_updated_at on leads;
create trigger trg_leads_updated_at
  before update on leads
  for each row execute function set_updated_at();

-- ----------------------------------------------------------------------------
-- lead_enrichment — contexto capturado por web scraping (1:1 com lead)
-- ----------------------------------------------------------------------------

create table if not exists lead_enrichment (
  id                 uuid primary key default gen_random_uuid(),
  lead_id            uuid not null unique references leads (id) on delete cascade,
  website_url        text,
  pages_scraped      jsonb not null default '[]'::jsonb,  -- URLs visitadas
  raw_content        text,                                -- texto bruto extraído (limitado)
  summary            text,                                -- resumo gerado pelo Claude
  industry           text,
  company_size_hint  text,
  security_context   jsonb,      -- ganchos p/ conversa: dores, produtos, compliance
  status             status_enriquecimento not null default 'pendente',
  error              text,
  scraped_at         timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

drop trigger if exists trg_lead_enrichment_updated_at on lead_enrichment;
create trigger trg_lead_enrichment_updated_at
  before update on lead_enrichment
  for each row execute function set_updated_at();

-- ----------------------------------------------------------------------------
-- conversations — sessões de conversa do agente (memória fica no LangChain)
-- ----------------------------------------------------------------------------
-- session_id é a chave usada pelo PostgresChatMessageHistory (langchain-postgres)
-- na tabela langchain_chat_history abaixo. Uma conversa por fase (pré/pós).

create table if not exists conversations (
  id          uuid primary key default gen_random_uuid(),
  lead_id     uuid not null references leads (id) on delete cascade,
  fase        fase_conversa not null,
  session_id  uuid not null unique default gen_random_uuid(),
  status      status_conversa not null default 'ativa',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (lead_id, fase)
);

create index if not exists idx_conversations_lead on conversations (lead_id);

drop trigger if exists trg_conversations_updated_at on conversations;
create trigger trg_conversations_updated_at
  before update on conversations
  for each row execute function set_updated_at();

-- ----------------------------------------------------------------------------
-- langchain_chat_history — memória nativa do LangChain
-- ----------------------------------------------------------------------------
-- Mesmo schema criado por PostgresChatMessageHistory.create_tables()
-- (langchain-postgres). O histórico é lido/escrito exclusivamente pelo
-- LangChain; o backend nunca manipula esta tabela diretamente.

create table if not exists langchain_chat_history (
  id          serial primary key,
  session_id  uuid not null,
  message     jsonb not null,
  created_at  timestamptz not null default now()
);

create index if not exists idx_langchain_chat_history_session
  on langchain_chat_history (session_id);

-- ----------------------------------------------------------------------------
-- notifications — régua de e-mails (lembretes e alertas)
-- ----------------------------------------------------------------------------

create table if not exists notifications (
  id             uuid primary key default gen_random_uuid(),
  lead_id        uuid references leads (id) on delete cascade,
  tipo           tipo_notificacao not null,
  canal          text not null default 'email',
  destinatario   text not null,
  scheduled_for  timestamptz not null,
  sent_at        timestamptz,
  status         status_notificacao not null default 'agendada',
  error          text,
  created_at     timestamptz not null default now(),
  unique (lead_id, tipo)   -- evita lembrete duplicado por lead
);

create index if not exists idx_notifications_due
  on notifications (status, scheduled_for);

-- ----------------------------------------------------------------------------
-- meetings — reuniões comerciais criadas pelo agente (Google Calendar)
-- ----------------------------------------------------------------------------

create table if not exists meetings (
  id               uuid primary key default gen_random_uuid(),
  lead_id          uuid not null references leads (id) on delete cascade,
  google_event_id  text,
  html_link        text,
  titulo           text,
  start_time       timestamptz not null,
  end_time         timestamptz not null,
  status           status_reuniao not null default 'agendada',
  created_at       timestamptz not null default now()
);

create index if not exists idx_meetings_lead on meetings (lead_id);

-- ----------------------------------------------------------------------------
-- agent_events — trilha de auditoria (tool calls, transições, erros)
-- ----------------------------------------------------------------------------

create table if not exists agent_events (
  id          uuid primary key default gen_random_uuid(),
  lead_id     uuid references leads (id) on delete cascade,
  event_type  text not null,     -- ex.: 'scraping_ok', 'tool_sheets_consulta', 'status_change'
  payload     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index if not exists idx_agent_events_lead on agent_events (lead_id, created_at desc);

-- ----------------------------------------------------------------------------
-- Views para o dashboard (Streamlit)
-- ----------------------------------------------------------------------------

create or replace view vw_funil as
select status, count(*)::int as total
from leads
group by status;

create or replace view vw_leads_por_dia as
select date_trunc('day', created_at)::date as dia, count(*)::int as total
from leads
group by 1
order by 1;

create or replace view vw_leads_por_cargo as
select cargo, count(*)::int as total
from leads
group by cargo;

-- ----------------------------------------------------------------------------
-- Segurança: RLS habilitado sem policies => somente service_role acessa.
-- ----------------------------------------------------------------------------

alter table leads                  enable row level security;
alter table lead_enrichment        enable row level security;
alter table conversations          enable row level security;
alter table langchain_chat_history enable row level security;
alter table notifications          enable row level security;
alter table meetings               enable row level security;
alter table agent_events           enable row level security;
