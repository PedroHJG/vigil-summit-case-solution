-- ============================================================================
-- Vigil Summit — Migration 0006: moderação de mensagens fora de contexto
--
-- Aplicar no SQL Editor do Supabase (após a 0005).
--
-- Protege contra abuso: leads que mandam muitas mensagens fora do tema do
-- evento (uso do WhatsApp como chatbot genérico) são bloqueados por 24h para
-- não gastar tokens do LLM à toa.
-- ============================================================================

-- Sequência de mensagens off-topic CONSECUTIVAS (reseta ao voltar ao contexto).
alter table leads add column if not exists off_topic_streak int not null default 0;

-- Até quando o atendimento automático deste lead está bloqueado (NULL = ativo).
alter table leads add column if not exists bloqueado_ate timestamptz;