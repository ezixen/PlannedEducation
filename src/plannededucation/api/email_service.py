"""
Email Service for PlannedEducation
Modular, optional email dispatch supporting:
1. Standard School / Campus SMTP (via aiosmtplib or smtplib)
2. Brevo (Sendinblue) Transactional REST API (free-tier friendly, 300 emails/day)
3. Zero-configuration Local/Console Logger (default for offline / self-contained school servers)

No paid services are ever required. All features are optional and fallback gracefully.
"""

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    """Check if any email provider (SMTP or Brevo) is configured."""
    return bool(os.getenv("BREVO_API_KEY") or os.getenv("SMTP_HOST"))


def get_email_status() -> dict:
    """Return status metadata about email configuration without exposing secrets."""
    brevo_configured = bool(os.getenv("BREVO_API_KEY"))
    smtp_host = os.getenv("SMTP_HOST")
    return {
        "configured": is_email_configured(),
        "provider": "brevo" if brevo_configured else ("smtp" if smtp_host else "console_mock"),
        "smtp_host": smtp_host or None,
        "smtp_port": int(os.getenv("SMTP_PORT", "587")) if smtp_host else None,
        "email_from": os.getenv("EMAIL_FROM", "noreply@localhost"),
    }


async def send_email(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: str | None = None,
) -> bool:
    """
    Send an email via Brevo REST API, School SMTP, or fallback to log.
    Never throws unhandled exceptions; returns True on success or fallback.
    """
    email_from = os.getenv("EMAIL_FROM", "PlannedEducation <noreply@localhost>")
    brevo_api_key = os.getenv("BREVO_API_KEY")
    smtp_host = os.getenv("SMTP_HOST")

    # 1. Brevo REST API Dispatch (if configured)
    if brevo_api_key:
        try:
            import httpx

            # Extract name and address if formatted as "Name <email@domain>"
            sender_name = "PlannedEducation"
            sender_email = email_from
            if "<" in email_from and ">" in email_from:
                parts = email_from.split("<")
                sender_name = parts[0].strip() or sender_name
                sender_email = parts[1].replace(">", "").strip()

            payload = {
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": text_content,
            }
            if html_content:
                payload["htmlContent"] = html_content

            headers = {
                "api-key": brevo_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
                if res.status_code in (200, 201, 202):
                    logger.info("Successfully dispatched email to %s via Brevo", to_email)
                    return True
                else:
                    logger.warning("Brevo API responded with status %s: %s", res.status_code, res.text)
        except Exception as e:
            logger.error("Failed to send email via Brevo API: %s", e)

    # 2. Standard School SMTP Dispatch (if SMTP_HOST is set)
    if smtp_host:
        try:
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
            smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes") or smtp_port == 465

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = email_from
            msg["To"] = to_email

            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            if html_content:
                msg.attach(MIMEText(html_content, "html", "utf-8"))

            # Attempt async dispatch via aiosmtplib if available
            try:
                import aiosmtplib

                await aiosmtplib.send(
                    msg,
                    hostname=smtp_host,
                    port=smtp_port,
                    username=smtp_user,
                    password=smtp_password,
                    use_tls=smtp_use_ssl,
                    start_tls=smtp_use_tls and not smtp_use_ssl,
                    timeout=10.0,
                )
                logger.info("Dispatched email to %s via SMTP (%s:%s)", to_email, smtp_host, smtp_port)
                return True
            except ImportError:
                # Fallback to standard synchronous smtplib in a background thread
                def _send_sync():
                    if smtp_use_ssl:
                        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10.0)
                    else:
                        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10.0)
                    try:
                        if smtp_use_tls and not smtp_use_ssl:
                            server.starttls()
                        if smtp_user and smtp_password:
                            server.login(smtp_user, smtp_password)
                        server.send_message(msg)
                    finally:
                        server.quit()

                await asyncio.to_thread(_send_sync)
                logger.info("Dispatched email to %s via sync smtplib (%s:%s)", to_email, smtp_host, smtp_port)
                return True

        except Exception as e:
            logger.error("Failed to send email via SMTP (%s): %s", smtp_host, e)

    # 3. Offline / Mock Logger Fallback (Zero-config school environment)
    logger.info(
        "[EMAIL LOG] To: %s | Subject: %s | Content: %s",
        to_email,
        subject,
        text_content.replace("\n", " "),
    )
    return True


async def send_password_reset_email(
    to_email: str,
    reset_link_or_token: str,
    username: str | None = None,
) -> bool:
    """Format and send a 24-hour secure password reset link to the user."""
    if reset_link_or_token.startswith("http://") or reset_link_or_token.startswith("https://"):
        reset_link = reset_link_or_token
    else:
        frontend_base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        reset_link = f"{frontend_base}/reset-password?token={reset_link_or_token}&email={to_email}"

    user_greeting = f"Hello {username or 'there'},"
    subject = "PlannedEducation — Password Reset Request"
    text_content = (
        f"{user_greeting}\n\n"
        f"A password reset was requested for your PlannedEducation account.\n\n"
        f"To set a new password, open this secure link in your browser:\n\n"
        f"    {reset_link}\n\n"
        f"This link is valid for 24 hours and can only be used once.\n\n"
        f"If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.\n\n"
        f"— The PlannedEducation System"
    )
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2563eb; margin-top: 0;">PlannedEducation</h2>
        <p>{user_greeting}</p>
        <p>A password reset was requested for your PlannedEducation account.</p>
        <p>Click the button below to reset your password. <strong>This link is valid for 24 hours</strong> and can only be used once:</p>
        <div style="text-align: center; margin: 28px 0;">
            <a href="{reset_link}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #64748b; font-size: 13px;">Or copy and paste this link into your browser:</p>
        <p style="color: #64748b; font-size: 12px; word-break: break-all;"><a href="{reset_link}">{reset_link}</a></p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">If you did not request this password reset, please ignore this email. Your password will remain unchanged.</p>
    </div>
    """
    return await send_email(to_email, subject, text_content, html_content)

