# Guia de testes locais

Como testar o funil inteiro — captação, qualificação, curadoria, confirmação, régua
proativa e follow-up pós-evento — sem esperar dias reais passarem, e como diagnosticar
os problemas mais comuns do ambiente local (Windows).

## O truque central: `EVENT_DATE`, nunca a data do PC

Toda a lógica de tempo do sistema (régua anti no-show, lembretes por e-mail, liberação
do follow-up pós-evento) compara a **hora real de agora** com a variável `EVENT_DATE`
(`backend/.env`). Para simular "o evento está chegando" ou "o evento já aconteceu",
**mude `EVENT_DATE`** — nunca o relógio do Windows.

Mudar a data do sistema quebraria TLS/HTTPS (Supabase, Anthropic, Google, Evolution
usam certificados validados por tempo), os tokens OAuth do Google, a sessão do
WhatsApp e o próprio Docker. `EVENT_DATE` resolve o mesmo problema sem nenhum efeito
colateral.

```env
# backend/.env
EVENT_DATE=2026-08-20T09:00:00-03:00   # ISO 8601 com offset de Brasília
```

Depois de editar, **reinicie o backend** — `get_settings()` usa `@lru_cache`, então o
processo em execução não vê a mudança sozinho:

```powershell
cd backend
.\restart.ps1
```

(`restart.ps1` mata quem estiver ouvindo a porta 8000 — incluindo workers órfãos de
`--reload` — e sobe o backend de novo com o `.venv` do projeto. Rode no PowerShell ou no
terminal integrado do VS Code; não funciona no `cmd.exe`.)

## Receita por toque da régua proativa

A régua (`cadence_service.py`) só dispara toques dentro da janela **08h–20h**
(horário de Brasília) e no máximo **1 toque por lead a cada 20h**. Para forçar o toque
que você quer ver, ajuste `EVENT_DATE` relativo a **hoje**:

| Quero ver | Pré-condição do lead | `EVENT_DATE` sugerido |
|---|---|---|
| `nudge_confirm_1` (1º lembrete de confirmação) | status `qualificado` há mais de 24h | qualquer data futura |
| `nudge_confirm_2` (2º lembrete, escassez) | `nudge_confirm_1` já enviado há 48h+ | idem |
| `last_call` (última chamada) | `qualificado`, evento em ≤ 2 dias | hoje + 2 dias |
| `companion` (convite a acompanhantes) | status `confirmado`, evento em ≤ 7 dias | hoje + 6 dias |
| `content` (antecipação de conteúdo) | `confirmado`, evento em ≤ 5 dias | hoje + 4 dias |
| `logistics` (véspera + assentos) | `confirmado`, evento em ≤ 1 dia | amanhã |
| `day_of` (lembrete do dia) | `confirmado`, faltam ≤ 3h | hoje, ~2h à frente da hora atual |

Depois de ajustar a data e reiniciar o backend, dispare a régua manualmente (ou espere
o cron horário do workflow **05** do n8n):

```powershell
curl -Method POST http://localhost:8000/api/v1/internal/cadence/run `
     -Headers @{"X-API-Key"="SEU_BACKEND_API_KEY"}
```

A resposta traz `toques_enviados: ["<lead_id>:<touchpoint>"]` — confirma o que saiu.

### Duas armadilhas dos testes repetidos

1. **Idempotência**: cada toque só sai 1 vez por lead (`unique(lead_id, touchpoint)` em
   `cadence_log`). Para forçar o mesmo toque de novo, limpe a linha:
   ```sql
   delete from cadence_log where lead_id = 'SEU_LEAD_ID';
   -- ou, para um toque específico:
   delete from cadence_log where lead_id = 'SEU_LEAD_ID' and touchpoint = 'companion';
   ```
2. **Lembretes por e-mail já agendados**: as linhas de `notifications` (D-7/D-1/H-2) são
   criadas com a data vigente no momento da confirmação e **não se reagendam sozinhas**
   se você mudar `EVENT_DATE` depois. Para retestar:
   ```sql
   delete from notifications where lead_id = 'SEU_LEAD_ID' and tipo like 'lembrete%';
   ```
   e rode `POST /internal/notifications/run` de novo (ou confirme o lead outra vez).

## Simulando o pós-evento (follow-up + agendamento de reunião)

1. `EVENT_DATE` no passado (ex.: ontem) + restart do backend.
2. Marque o lead como participante:
   ```sql
   update leads set status = 'compareceu' where id = 'SEU_LEAD_ID';
   ```
3. Dispare o follow-up:
   ```powershell
   curl -Method POST http://localhost:8000/api/v1/internal/follow-ups/run `
        -Headers @{"X-API-Key"="SEU_BACKEND_API_KEY"}
   ```
4. A Sofia abre uma **nova sessão de memória** (fase `pos_evento` — a conversa
   `pre_evento` é encerrada, não apagada) e conduz: impressão do evento → proposta de
   reunião → `verificar_disponibilidade` (free/busy **real** da sua agenda Google) →
   você escolhe um horário no WhatsApp → `agendar_reuniao` cria o evento na sua agenda
   com convite para o lead.

Para resetar o lead para uma nova rodada de teste sem recriá-lo:
```sql
update leads set status = 'confirmado' where id = 'SEU_LEAD_ID';
update conversations set status = 'ativa' where lead_id = 'SEU_LEAD_ID' and fase = 'pre_evento';
delete from conversations where lead_id = 'SEU_LEAD_ID' and fase = 'pos_evento';
```

## Testar o agente sem WhatsApp

Sem Evolution configurada (ou para depurar prompts rapidamente), converse direto no
terminal — usa a mesma chain, tools e memória do fluxo real:

```powershell
cd backend
python -m scripts.chat_local <lead_id>          # fase pré-evento
python -m scripts.chat_local <lead_id> pos       # fase pós-evento
```

Digite `kickoff` para disparar a primeira mensagem da fase (equivalente ao que o n8n
dispararia); `sair` para encerrar.

## Problemas comuns e como diagnosticar

### "O agente parou de responder" no meio de uma conversa

Sintoma: você manda mensagem no WhatsApp e nada volta. Causas mais prováveis, em ordem:

1. **Token OAuth do Google expirado.** Enquanto o app OAuth estiver em modo *Testing*
   no Google Cloud Console, o `refresh_token` expira em **7 dias**. Isso derruba
   silenciosamente qualquer turno que use `verificar_disponibilidade`/`agendar_reuniao`
   — o sintoma é exatamente "o agente sumiu" (o backend tem uma rede de segurança que
   envia uma mensagem de desculpas ao lead nesse caso, mas o agendamento real só volta
   a funcionar depois de renovar o token). Corrija com:
   ```powershell
   cd backend
   python -m scripts.google_oauth_setup
   ```
   Isso abre o navegador — faça login com a conta dona da agenda e autorize de novo.
   Para eliminar essa manutenção recorrente, publique o app OAuth em "Production" na
   tela de consentimento do Google Cloud (não exige verificação do Google para uso
   próprio com o escopo `calendar`).
2. **Backend não está rodando** — confira `http://localhost:8000/health`.
3. **Instância da Evolution desconectada** — confira `http://localhost:8080/manager`,
   o status da instância deve estar `open` (se cair, escaneie o QR code de novo).
4. Confira o terminal do backend por um traceback — qualquer exceção não prevista por
   uma tool aparece ali com `logger.exception(...)`.

### Formulário não envia pelo celular

- O form usa `http://${window.location.hostname}:8000` como URL do backend por padrão
  (mesmo host que serviu a página) — confirme que `Landing page VIGIL SUMMIT/.env` **não**
  tem `VITE_API_URL` ativa sobrescrevendo isso (se tiver, comente a linha e reinicie o
  `npm run dev`).
- O **Firewall do Windows** bloqueia conexões de entrada por padrão em redes marcadas
  como "Public" — e as regras de firewall são por **executável**, não por porta: uma
  regra liberando `python.exe` do Python do sistema não cobre o `python.exe` do
  `.venv` do projeto. Crie uma regra específica de porta:
  ```powershell
  New-NetFirewallRule -DisplayName "Vigil Summit Backend (porta 8000)" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Any
  ```
  (pede elevação de administrador na primeira vez).
- Descubra o IP atual do PC na rede Wi-Fi (`ipconfig` → "Endereço IPv4") e acesse do
  celular por `http://SEU_IP:5173` — o IP pode mudar a cada reconexão do roteador
  (considere reservar o IP do PC no DHCP do roteador se for testar com frequência).

### "Porta já em uso" ao subir o backend/dashboard

Processos órfãos de sessões anteriores (ex.: um `uvicorn --reload` cujo processo pai
já morreu) continuam ouvindo a porta. No PowerShell:
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```
(troque `8000` por `8501` para o dashboard). O script `backend/restart.ps1` já faz isso
para o backend automaticamente.