"""Envio de e-mails transacionais via SMTP (Gmail com app password).

EMAIL_MOCK_MODE=true permite demonstrar o fluxo completo sem credenciais:
os envios são apenas logados.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import get_settings

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type((smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    reraise=True,
)
def send_email(to: str, subject: str, html: str) -> None:
    settings = get_settings()

    if settings.email_mock_mode:
        logger.info("[EMAIL MOCK] para=%s assunto=%s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(msg["From"], [to], msg.as_string())

    logger.info("E-mail enviado para %s: %s", to, subject)


# =============================================================================
# Templates (HTML simples, responsivo por natureza)
# =============================================================================

def _wrap(body: str) -> str:
    settings = get_settings()
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;color:#181818">
      <div style="background:#181818;padding:24px;text-align:center">
        <span style="color:#b341f2;font-size:20px;font-weight:bold">{settings.event_name}</span>
      </div>
      <div style="padding:24px;line-height:1.6">{body}</div>
      <div style="padding:16px;text-align:center;color:#888;font-size:12px">
        Você recebeu este e-mail porque se inscreveu no {settings.event_name}.
      </div>
    </div>"""


def build_confirmation(lead: dict) -> tuple[str, str]:
    s = get_settings()
    primeiro_nome = lead["nome"].split()[0]
    subject = f"Inscrição recebida — {s.event_name}"
    body = f"""
      <h2>Olá, {primeiro_nome}!</h2>
      <p>Recebemos sua solicitação de convite para o <strong>{s.event_name}</strong>.</p>
      <p><strong>Data:</strong> {s.event_date.strftime('%d/%m/%Y às %H:%M')}<br>
         <strong>Local:</strong> {s.event_location}</p>
      <p>Nosso time entrará em contato pelo WhatsApp para concluir a curadoria do seu convite.
         Fique de olho no número cadastrado.</p>"""
    return subject, _wrap(body)


def build_inscricao_confirmada(lead: dict) -> tuple[str, str]:
    from datetime import timedelta

    from agent.tools.calendar import build_add_to_calendar_link

    s = get_settings()
    primeiro_nome = lead["nome"].split()[0]
    link_agenda = build_add_to_calendar_link(
        s.event_name,
        s.event_date,
        s.event_date + timedelta(hours=8),
        s.event_location,
        f"Inscrição confirmada. Detalhes: {s.event_landing_url}",
    )
    subject = f"🎟️ Inscrição confirmada — {s.event_name}"
    body = f"""
      <h2>{primeiro_nome}, sua vaga está garantida!</h2>
      <p>Sua inscrição no <strong>{s.event_name}</strong> foi confirmada.</p>
      <p><strong>Data:</strong> {s.event_date.strftime('%d/%m/%Y às %H:%M')}<br>
         <strong>Local:</strong> {s.event_location}</p>
      <p style="margin:24px 0">
        <a href="{link_agenda}"
           style="background:#8d2fc3;color:#fff;padding:12px 20px;border-radius:8px;
                  text-decoration:none;font-weight:bold">
          📅 Adicionar à minha agenda
        </a>
      </p>
      <p>Você também receberá lembretes por e-mail conforme a data se aproximar.
         Até lá!</p>"""
    return subject, _wrap(body)


def build_reminder(lead: dict, tipo: str) -> tuple[str, str]:
    s = get_settings()
    primeiro_nome = lead["nome"].split()[0]
    quando = {
        "lembrete_d7": "é daqui a uma semana",
        "lembrete_d1": "é amanhã",
        "lembrete_h2": "começa em 2 horas",
    }.get(tipo, "está chegando")
    subject = f"⏰ {s.event_name} {quando}!"
    body = f"""
      <h2>{primeiro_nome}, o evento {quando}!</h2>
      <p><strong>Data:</strong> {s.event_date.strftime('%d/%m/%Y às %H:%M')}<br>
         <strong>Local:</strong> {s.event_location}</p>
      <p>Prepare suas perguntas sobre segurança na era da IA — nossos especialistas
         estarão à disposição.</p>"""
    return subject, _wrap(body)


def build_internal_alert(lead: dict, motivo: str) -> tuple[str, str]:
    subject = f"[ALERTA] Lead qualificado: {lead['nome']} ({lead['empresa']})"
    body = f"""
      <h2>Novo lead qualificado</h2>
      <p><strong>Nome:</strong> {lead['nome']}<br>
         <strong>Cargo:</strong> {lead.get('cargo_validado') or lead['cargo']}<br>
         <strong>Empresa:</strong> {lead['empresa']}<br>
         <strong>E-mail:</strong> {lead['email']}<br>
         <strong>WhatsApp:</strong> {lead['telefone_e164']}<br>
         <strong>LinkedIn:</strong> {lead.get('linkedin_url') or '—'}</p>
      <p><strong>Motivo:</strong> {motivo}</p>"""
    return subject, _wrap(body)
