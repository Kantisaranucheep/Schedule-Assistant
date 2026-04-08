"""Email service for sending notification emails via SMTP."""

import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.settings = get_settings()
        self._validate_config()

    def _get_config_status(self) -> Dict[str, Optional[str]]:
        """Get the status of each SMTP configuration variable."""
        return {
            "SMTP_HOST": self.settings.smtp_host,
            "SMTP_PORT": str(self.settings.smtp_port),
            "SMTP_USERNAME": self.settings.smtp_username,
            "SMTP_PASSWORD": self.settings.smtp_password,
            "SMTP_FROM_EMAIL": self.settings.smtp_from_email,
            "SMTP_FROM_NAME": self.settings.smtp_from_name,
        }

    def _validate_config(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(
            self.settings.smtp_username and
            self.settings.smtp_password and
            self.settings.smtp_from_email
        )

    def get_config_error_message(self) -> str:
        """Get a detailed error message showing all SMTP variables from .env."""
        config = self._get_config_status()

        # Format each config item
        config_lines = []
        for key, value in config.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                formatted_value = "null"
            elif key == "SMTP_PASSWORD":
                # Hide actual password, just show it's set
                formatted_value = "***hidden***"
            else:
                formatted_value = str(value)

            config_lines.append(f"{key} = {formatted_value}")

        # Mark required fields
        required_fields = {"SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"}
        config_with_status = []
        for line in config_lines:
            field_name = line.split(" = ")[0]
            if field_name in required_fields:
                config_with_status.append(f"{line} (required)")
            else:
                config_with_status.append(f"{line} (optional)")

        config_display = "\n".join(config_with_status)

        return f"""Email service not configured properly. Check your .env file:

{config_display}

Please ensure all REQUIRED fields are set."""

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self._validate_config()

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, derived from HTML if not provided)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_configured():
            error_msg = self.get_config_error_message()
            logger.warning(error_msg)
            return False, error_msg

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
            message["To"] = to_email

            # Add plain text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, "plain")
                message.attach(part1)

            part2 = MIMEText(body_html, "html")
            message.attach(part2)

            # Create secure SSL context
            context = ssl.create_default_context()

            # Send email
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.sendmail(
                    self.settings.smtp_from_email,
                    to_email,
                    message.as_string()
                )

            logger.info(f"Email sent successfully to {to_email}")
            return True, f"Email sent successfully to {to_email}"

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {e}"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error sending email: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error sending email: {e}"
            logger.error(error_msg)
            return False, error_msg

    def send_event_notification(
        self,
        to_email: str,
        event_title: str,
        event_start: datetime,
        event_location: Optional[str] = None,
        event_notes: Optional[str] = None,
        minutes_before: int = 0
    ) -> bool:
        """
        Send an event notification email.

        Args:
            to_email: Recipient email address
            event_title: Title of the event
            event_start: Event start datetime
            event_location: Optional event location
            event_notes: Optional event notes/description
            minutes_before: How many minutes before the event this notification is for

        Returns:
            True if email sent successfully
        """
        # Format the time string
        time_str = event_start.strftime("%A, %B %d, %Y at %I:%M %p")

        # Create notification timing text
        if minutes_before >= 1440:
            days = minutes_before // 1440
            timing = f"{days} day{'s' if days > 1 else ''}"
        elif minutes_before >= 60:
            hours = minutes_before // 60
            timing = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            timing = f"{minutes_before} minute{'s' if minutes_before > 1 else ''}"

        subject = f"📅 Reminder: {event_title} - {timing} from now"

        # HTML email body
        location_html = f"<p><strong>📍 Location:</strong> {event_location}</p>" if event_location else ""
        notes_html = f"<p><strong>📝 Notes:</strong></p><p style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>{event_notes}</p>" if event_notes else ""

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }}
                .event-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .timing {{ color: #667eea; font-size: 18px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Event Reminder</h1>
                </div>
                <div class="content">
                    <p class="timing">Starting in {timing}!</p>
                    <div class="event-card">
                        <h2>📌 {event_title}</h2>
                        <p><strong>🕐 When:</strong> {time_str}</p>
                        {location_html}
                        {notes_html}
                    </div>
                    <p style="margin-top: 20px;">Don't forget to prepare for your upcoming event!</p>
                </div>
                <div class="footer">
                    <p>This is an automated reminder from Schedule Assistant.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        notes_text = f"\n📝 Notes:\n{event_notes}\n" if event_notes else ""
        body_text = f"""
Event Reminder - Starting in {timing}!

📌 {event_title}
🕐 When: {time_str}
{"📍 Location: " + event_location if event_location else ""}{notes_text}
Don't forget to prepare for your upcoming event!

---
This is an automated reminder from Schedule Assistant.
        """

        success, _ = self.send_email(to_email, subject, body_html, body_text)
        return success


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
