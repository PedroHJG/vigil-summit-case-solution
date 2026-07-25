-- ============================================================================
-- Vigil Summit — Migration 0005: aderência do setor da empresa ao ICP
--
-- Aplicar no SQL Editor do Supabase (após a 0004).
--
-- setor_score (0-100): quão aderente é o setor da empresa ao público/tema do
-- evento (tecnologia/segurança e setores regulados = alto; varejo etc = baixo).
-- Classificado pelo Claude no enriquecimento. NÃO é eliminatório — ajusta o
-- score de qualificação e a probabilidade de presença (ver dashboard/scoring).
-- ============================================================================

alter table leads add column if not exists setor_score int
  check (setor_score is null or (setor_score >= 0 and setor_score <= 100));