import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.models.all_models import EmailLog

async def send_transactional_email(
    db: AsyncSession,
    recipient: str,
    subject: str,
    template_name: str,
    html_content: str,
    reference_id: Optional[str] = None
) -> bool:
    """
    Sends transactional, request-triggered emails via Gmail SMTP.
    Logs dispatch record in email_logs table.
    Fulfills REQ-INF-56.
    """
    email_status = "SENT"
    
    # If live credentials are provided in settings, dispatch via Gmail SMTP
    if settings.GMAIL_SENDER_EMAIL and settings.GMAIL_APP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.GMAIL_SENDER_EMAIL
            msg["To"] = recipient
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(settings.GMAIL_SMTP_HOST, settings.GMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(settings.GMAIL_SENDER_EMAIL, settings.GMAIL_APP_PASSWORD)
                server.sendmail(settings.GMAIL_SENDER_EMAIL, recipient, msg.as_string())
        except Exception as e:
            email_status = f"FAILED: {str(e)[:100]}"
    else:
        # In development/test mode without active credentials, record as simulated sent
        email_status = "SIMULATED_SENT"

    log_entry = EmailLog(
        id=str(uuid.uuid4()),
        recipient=recipient,
        subject=subject,
        template_name=template_name,
        reference_id=reference_id,
        status=email_status,
        sent_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    return True
