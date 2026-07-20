-- ============================================================================
-- Vigil Summit — Migration 0002: curadoria via Sheets + confirmação de inscrição
--
-- Aplicar no SQL Editor do Supabase (após a 0001).
-- ============================================================================

-- Quantidade de funcionários informada pelo lead na qualificação
-- (texto livre: "850", "entre 200 e 500" etc. — quem interpreta é o agente)
alter table leads add column if not exists funcionarios text;

-- Novo e-mail transacional: confirmação efetiva da inscrição (pós-botão).
-- O 'confirmacao_inscricao' original passa a ser o "recebemos sua solicitação".
alter type tipo_notificacao add value if not exists 'inscricao_confirmada';

-- Evento do próprio summit criado na agenda quando o lead confirma
-- (reuso da tabela meetings, diferenciado pelo campo tipo)
alter table meetings add column if not exists tipo text not null default 'reuniao_comercial';