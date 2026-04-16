"""SMTP email service for verification and reset emails (AUTH-005)."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings


class EmailService:
    """Thin SMTP wrapper. Raises on send failure — caller handles."""

    def _send(self, to: str, subject: str, body_html: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            if settings.SMTP_USER:
                smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM, to, msg.as_string())

    def send_verification_email(self, to: str, raw_token: str) -> None:
        """Send account verification email with single-use link."""
        link = f"{settings.APP_BASE_URL}/auth/verify-email?token={raw_token}"
        self._send(
            to=to,
            subject="Verify your Briefly account",
            body_html=(
                f"<p>Welcome to Briefly!</p>"
                f"<p>Click to verify your email (expires in 24h):</p>"
                f"<p><a href='{link}'>{link}</a></p>"
                f"<p>If you didn't create an account, ignore this email.</p>"
            ),
        )

    def send_password_reset_email(self, to: str, raw_token: str) -> None:
        """Send password reset email with single-use link."""
        link = f"{settings.APP_BASE_URL}/auth/reset-password?token={raw_token}"
        self._send(
            to=to,
            subject="Reset your Briefly password",
            body_html=(
                f"<p>Click to reset your password (expires in 1h):</p>"
                f"<p><a href='{link}'>{link}</a></p>"
                f"<p>If you didn't request this, ignore this email.</p>"
            ),
        )
