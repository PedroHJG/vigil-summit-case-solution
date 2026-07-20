-- ============================================================================
-- Vigil Summit — Migration 0003: acompanhantes + régua proativa anti no-show
--
-- Aplicar no SQL Editor do Supabase (após a 0002).
-- ============================================================================

-- Quantidade de acompanhantes que o lead levará ao evento (máximo 2)
alter table leads add column if not exists acompanhantes int not null default 0
  check (acompanhantes >= 0 and acompanhantes <= 2);

-- Log da régua proativa de WhatsApp (1 linha por toque enviado por lead).
-- unique(lead_id, touchpoint) garante que cada toque é enviado no máximo 1 vez.
create table if not exists cadence_log (
  id          uuid primary key default gen_random_uuid(),
  lead_id     uuid not null references leads (id) on delete cascade,
  touchpoint  text not null,      -- nudge_confirm_1, nudge_confirm_2, last_call,
                                  -- companion, content, logistics, day_of
  sent_at     timestamptz not null default now(),
  respondido  boolean not null default false,
  unique (lead_id, touchpoint)
);

create index if not exists idx_cadence_log_lead on cadence_log (lead_id, sent_at desc);

alter table cadence_log enable row level security;