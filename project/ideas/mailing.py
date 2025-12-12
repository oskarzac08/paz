import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_verification_code(email: str, code: str) -> None:
    subject = "Kod weryfikacyjny"
    message = f"Twój kod weryfikacyjny to: {code}\nWażny przez 10 minut."

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

    logger.info("Verification code for %s: %s", email, code)
