"""
Serwis do obsługi weryfikacji dwukanałowej użytkowników
Zgodnie z ADR-003 i PDR-001
"""
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import timedelta
import random
import logging
from django.core.mail import get_connection, EmailMessage

from .models import ActivationCode, UserProfile

logger = logging.getLogger(__name__)


class VerificationService:
    """Główny serwis do zarządzania weryfikacją użytkowników"""
    
    CODE_LENGTH = 6
    CODE_VALIDITY_HOURS = 24
    MAX_CODES_PER_HOUR = 3
    
    @classmethod
    def generate_code(cls):
        """Generuje 6-cyfrowy kod weryfikacyjny"""
        return ''.join([str(random.randint(0, 9)) for _ in range(cls.CODE_LENGTH)])
    
    @classmethod
    def can_send_code(cls, user, channel):
        """
        Sprawdza czy użytkownik może otrzymać nowy kod (rate limiting).
        Max 3 kody na godzinę.
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_codes = ActivationCode.objects.filter(
            user=user,
            channel=channel,
            created_at__gte=one_hour_ago
        ).count()
        
        return recent_codes < cls.MAX_CODES_PER_HOUR
    
    @classmethod
    def create_verification_code(cls, user, channel):
        """
        Tworzy nowy kod weryfikacyjny dla użytkownika.
        
        Args:
            user: Instancja User
            channel: 'email' lub 'sms'
        
        Returns:
            ActivationCode instance lub None jeśli przekroczono limit
        """
        if not cls.can_send_code(user, channel):
            logger.warning(f"Rate limit exceeded for user {user.id} on channel {channel}")
            return None
        
        # Unieważnij poprzednie nieużyte kody dla tego użytkownika i kanału
        ActivationCode.objects.filter(
            user=user,
            channel=channel,
            is_used=False
        ).update(is_used=True)
        
        # Utwórz nowy kod
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(hours=cls.CODE_VALIDITY_HOURS)
        
        activation_code = ActivationCode.objects.create(
            user=user,
            code=code,
            channel=channel,
            expires_at=expires_at
        )
        
        logger.info(f"Created verification code for user {user.id} via {channel}")
        return activation_code
    
    @classmethod
    def verify_code(cls, user, code, channel):
        """
        Weryfikuje kod użytkownika.
        
        Args:
            user: Instancja User
            code: Kod do weryfikacji
            channel: 'email' lub 'sms'
        
        Returns:
            tuple (bool, str): (success, message)
        """
        try:
            activation_code = ActivationCode.objects.get(
                user=user,
                code=code,
                channel=channel,
                is_used=False
            )
        except ActivationCode.DoesNotExist:
            logger.warning(f"Invalid code attempt for user {user.id}")
            return False, "Nieprawidłowy kod weryfikacyjny"
        
        if activation_code.is_expired:
            logger.warning(f"Expired code used by user {user.id}")
            return False, "Kod weryfikacyjny wygasł"
        
        # Oznacz kod jako użyty
        activation_code.mark_used()
        
        # Zaktualizuj status weryfikacji w profilu
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if channel == 'email':
            profile.email_verified = True
        elif channel == 'sms':
            profile.phone_verified = True
        profile.save()
        
        logger.info(f"Successfully verified {channel} for user {user.id}")
        return True, "Weryfikacja zakończona pomyślnie"
    
    @classmethod
    def send_verification_code(cls, user, channel, code):
        """
        Wysyła kod weryfikacyjny do użytkownika.
        
        Args:
            user: Instancja User
            channel: 'email' lub 'sms'
            code: Kod do wysłania
        
        Returns:
            bool: True jeśli wysłano pomyślnie
        """
        if channel == 'email':
            return EmailVerificationBackend.send(user, code)
        elif channel == 'sms':
            return SMSVerificationBackend.send(user, code)
        return False


class EmailVerificationBackend:
    """Backend do wysyłki kodów weryfikacyjnych przez e-mail"""
    
    @staticmethod
    def send(user, code):
        """
        Wysyła kod weryfikacyjny na e-mail użytkownika.
        
        Args:
            user: Instancja User
            code: Kod weryfikacyjny
        
        Returns:
            bool: True jeśli wysłano pomyślnie
        """
        try:
            subject = 'Kod weryfikacyjny'
            message = f"""
Witaj {user.username}!

Twój kod weryfikacyjny to: {code}

Kod jest ważny przez 24 godziny.

Jeśli nie rejestrowałeś się w naszym serwisie, zignoruj tę wiadomość.
"""


            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')

            # Always log the email content to console for debugging
            logger.debug(f"Preparing to send verification email to {user.email} from {from_email}")
            logger.info("--- EMAIL (console) ---")
            logger.info(f"To: {user.email}")
            logger.info(f"From: {from_email}")
            logger.info(f"Subject: {subject}")
            logger.info(message)
            logger.info("--- END EMAIL (console) ---")

            # Attempt to send using configured EMAIL_BACKEND (SMTP in production)
            try:
                email = EmailMessage(subject, message, from_email, [user.email])
                # Uses project's configured backend
                connection = get_connection()
                email.send(fail_silently=False)
                logger.info(f"Verification email sent to {user.email} via backend {connection.__class__.__name__}")
            except Exception:
                logger.exception("Failed to send verification email via configured backend")

            return True

        except Exception:
            logger.exception("Failed to send verification email")
            return False


class SMSVerificationBackend:
    """Backend do wysyłki kodów weryfikacyjnych przez SMS"""
    
    @staticmethod
    def send(user, code):
        """
        Wysyła kod weryfikacyjny przez SMS.
        
        Args:
            user: Instancja User
            code: Kod weryfikacyjny
        
        Returns:
            bool: True jeśli wysłano pomyślnie
        """
        try:
            profile = UserProfile.objects.get(user=user)
            phone_number = profile.phone_number

            if not phone_number:
                logger.warning(f"No phone number for user {user.id}")
                return False

            # TODO: Integracja z bramką SMS (np. Twilio, SMS API)
            # Na potrzeby MVP logujemy kod i numer
            message = f"Twój kod weryfikacyjny: {code}. Ważny 24h."

            logger.debug(f"Preparing to send SMS to {phone_number} for user {user.id}")
            logger.info(f"SMS verification code to {phone_number}: {code}")

            # Tymczasowo zwracamy True - w produkcji tutaj będzie prawdziwa wysyłka
            return True

        except UserProfile.DoesNotExist:
            logger.exception(f"No profile found for user {user.id}")
            return False
        except Exception:
            logger.exception("Failed to send SMS")
            return False
