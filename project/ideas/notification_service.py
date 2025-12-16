"""
Serwis powiadomień - zarządzanie wysyłką powiadomień email i SMS

Zgodnie z ADR-007 i PDR-007
"""

from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth import get_user_model
import logging

from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

User = get_user_model()


class NotificationService:
    """
    Główny serwis do tworzenia i wysyłania powiadomień
    """
    
    @staticmethod
    def create_notification(user, notification_type, channel=None, context=None, related_obj=None):
        """
        Tworzy powiadomienie i wysyła je (synchronicznie w MVP, asynchronicznie z Celery w produkcji)
        
        Args:
            user: Użytkownik (User object)
            notification_type: Typ powiadomienia (string z Notification.TYPE_CHOICES)
            channel: Kanał ('email', 'sms', lub None = auto z preferencji)
            context: Dict z danymi do template
            related_obj: Powiązany obiekt (Reservation, ActivationCode, etc.)
        
        Returns:
            Notification object lub None jeśli użytkownik wyłączył powiadomienia
        """
        # Sprawdź preferencje użytkownika
        try:
            prefs = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            # Utwórz domyślne preferencje jeśli nie istnieją
            prefs = NotificationPreference.objects.create(user=user)
        
        # Sprawdź czy użytkownik chce ten typ powiadomienia
        if not prefs.should_send_notification(notification_type):
            logger.info(f"User {user.id} opted out of {notification_type}")
            return None
        
        # Określ kanał
        if channel is None:
            # Auto-detect na podstawie preferencji
            channel = NotificationService._get_preferred_channel(user, prefs)
        
        # Określ odbiorcę na podstawie kanału
        if channel == 'email':
            recipient = user.email
            if not recipient:
                logger.warning(f"User {user.id} has no email, cannot send email notification")
                return None
        elif channel == 'sms':
            try:
                recipient = user.profile.phone_number
                if not recipient:
                    logger.warning(f"User {user.id} has no phone, cannot send SMS notification")
                    # Fallback do email
                    channel = 'email'
                    recipient = user.email
            except Exception as e:
                logger.warning(f"Cannot get phone for user {user.id}: {e}, falling back to email")
                channel = 'email'
                recipient = user.email
        else:
            raise ValueError(f"Unsupported channel: {channel}")
        
        # Przygotuj kontekst dla template
        context = context or {}
        context.setdefault('user', user)
        context.setdefault('site_name', getattr(settings, 'SITE_NAME', 'System Rezerwacji'))
        
        # Renderuj wiadomość z template
        try:
            message = NotificationService._render_message(notification_type, channel, context)
            subject = context.get('subject', NotificationService._get_default_subject(notification_type))
            
            # Dla email - opcjonalnie HTML
            html_message = ''
            if channel == 'email':
                html_message = NotificationService._render_html_message(notification_type, context)
        except Exception as e:
            logger.error(f"Failed to render message for {notification_type}/{channel}: {e}")
            # Fallback do prostej wiadomości
            message = context.get('message', f"Powiadomienie: {notification_type}")
            subject = context.get('subject', 'Powiadomienie')
            html_message = ''
        
        # Utwórz notification w bazie
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            message=message,
            html_message=html_message,
            related_object_type=type(related_obj).__name__ if related_obj else '',
            related_object_id=related_obj.id if related_obj and hasattr(related_obj, 'id') else None,
            status='pending'
        )
        
        # Wyślij synchronicznie (w MVP)
        # W produkcji: użyj Celery task
        # from .tasks import send_notification_task
        # send_notification_task.delay(notification.id)
        
        success = NotificationService._send_notification_sync(notification)
        
        if success:
            logger.info(f"Notification {notification.id} sent successfully")
        else:
            logger.warning(f"Notification {notification.id} failed to send")
        
        return notification
    
    @staticmethod
    def _get_preferred_channel(user, prefs):
        """Określa preferowany kanał na podstawie preferencji"""
        if prefs.preferred_channel == 'both':
            # Dla 'both' preferujemy email (tańsze)
            return 'email'
        return prefs.preferred_channel
    
    @staticmethod
    def _render_message(notification_type, channel, context):
        """Renderuje wiadomość z template"""
        template_name = f'notifications/{notification_type}_{channel}.txt'
        try:
            return render_to_string(template_name, context)
        except Exception:
            # Fallback template
            template_name = f'notifications/default_{channel}.txt'
            return render_to_string(template_name, context)
    
    @staticmethod
    def _render_html_message(notification_type, context):
        """Renderuje HTML wiadomość dla email"""
        template_name = f'notifications/{notification_type}_email.html'
        try:
            return render_to_string(template_name, context)
        except Exception:
            # Brak HTML template - zwróć pusty string
            return ''
    
    @staticmethod
    def _get_default_subject(notification_type):
        """Zwraca domyślny temat dla typu powiadomienia"""
        subjects = {
            'verification_code': 'Kod weryfikacyjny',
            'booking_confirmation': 'Potwierdzenie rezerwacji',
            'booking_reminder_24h': 'Przypomnienie o wizycie',
            'booking_reminder_2h': 'Wizyta za 2 godziny',
            'booking_cancelled': 'Wizyta odwołana',
            'booking_modified': 'Zmiana w wizycie',
            'staff_new_booking': 'Nowa rezerwacja',
            'staff_cancellation': 'Klient odwołał wizytę',
            'staff_daily_report': 'Raport dzienny',
            'staff_weekly_report': 'Raport tygodniowy',
        }
        return subjects.get(notification_type, 'Powiadomienie')
    
    @staticmethod
    def _send_notification_sync(notification):
        """
        Wysyła powiadomienie synchronicznie
        W produkcji zastąpić przez Celery task
        """
        try:
            if notification.channel == 'email':
                return EmailBackend.send(notification)
            elif notification.channel == 'sms':
                return SMSBackend.send(notification)
            else:
                logger.error(f"Unknown channel: {notification.channel}")
                return False
        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")
            notification.mark_failed(str(e))
            return False
    
    # === Specjalizowane metody dla różnych typów powiadomień ===
    
    @staticmethod
    def send_booking_confirmation(reservation):
        """Wysyła potwierdzenie rezerwacji"""
        user = reservation.user
        if not user:
            logger.warning(f"Cannot send booking confirmation - no user for reservation {reservation.id}")
            return None
        
        # Określ kanał
        try:
            channel = user.notification_preferences.preferred_channel
            if channel == 'both':
                channel = 'email'  # Domyślnie email
        except Exception:
            channel = 'email'
        
        context = {
            'user': user,
            'reservation': reservation,
            'service': reservation.service,
            'start': reservation.start,
            'end': reservation.end,
            'cancellation_url': NotificationService._get_cancellation_url(reservation),
            'subject': f'Potwierdzenie rezerwacji - {reservation.service.name}',
        }
        
        return NotificationService.create_notification(
            user=user,
            notification_type='booking_confirmation',
            channel=channel,
            context=context,
            related_obj=reservation
        )
    
    @staticmethod
    def send_booking_reminder(reservation, hours_before=24):
        """Wysyła przypomnienie o wizycie"""
        user = reservation.user
        if not user:
            return None
        
        # Określ typ na podstawie czasu
        notification_type = 'booking_reminder_24h' if hours_before >= 24 else 'booking_reminder_2h'
        
        # Dla przypomnienia 2h preferuj SMS jeśli dostępny
        try:
            prefs = user.notification_preferences
            if hours_before < 24 and prefs.preferred_channel in ['sms', 'both']:
                if user.profile.phone_number:
                    channel = 'sms'
                else:
                    channel = 'email'
            else:
                channel = prefs.preferred_channel if prefs.preferred_channel != 'both' else 'email'
        except Exception:
            channel = 'email'
        
        context = {
            'user': user,
            'reservation': reservation,
            'service': reservation.service,
            'start': reservation.start,
            'hours_before': hours_before,
            'cancellation_url': NotificationService._get_cancellation_url(reservation),
            'subject': f'Przypomnienie o wizycie - {reservation.service.name}',
        }
        
        return NotificationService.create_notification(
            user=user,
            notification_type=notification_type,
            channel=channel,
            context=context,
            related_obj=reservation
        )
    
    @staticmethod
    def send_cancellation_notification(reservation, cancelled_by):
        """Powiadamia o odwołaniu wizyty"""
        user = reservation.user
        if not user:
            return None
        
        context = {
            'user': user,
            'reservation': reservation,
            'service': reservation.service,
            'cancelled_by': cancelled_by,
            'cancelled_by_staff': reservation.cancelled_by_staff,
            'cancellation_reason': reservation.get_cancellation_reason_display() if reservation.cancellation_reason else '',
            'subject': f'Wizyta odwołana - {reservation.service.name}',
        }
        
        # Powiadom klienta
        client_notification = NotificationService.create_notification(
            user=user,
            notification_type='booking_cancelled',
            context=context,
            related_obj=reservation
        )
        
        # Jeśli klient odwołał - powiadom obsługę
        if not reservation.cancelled_by_staff:
            NotificationService._notify_staff_about_cancellation(reservation)
        
        return client_notification
    
    @staticmethod
    def send_booking_modified_notification(reservation):
        """Powiadamia o zmianie w wizycie"""
        user = reservation.user
        if not user:
            return None
        
        context = {
            'user': user,
            'reservation': reservation,
            'service': reservation.service,
            'start': reservation.start,
            'subject': f'Zmiana w wizycie - {reservation.service.name}',
        }
        
        return NotificationService.create_notification(
            user=user,
            notification_type='booking_modified',
            context=context,
            related_obj=reservation
        )
    
    @staticmethod
    def _notify_staff_about_cancellation(reservation):
        """Powiadamia obsługę o odwołaniu przez klienta"""
        # Znajdź użytkowników z grupą Staff
        staff_users = User.objects.filter(groups__name='Staff').distinct()
        
        for staff in staff_users:
            context = {
                'user': staff,
                'reservation': reservation,
                'client': reservation.user,
                'service': reservation.service,
                'subject': f'Klient odwołał wizytę - {reservation.service.name}',
            }
            
            NotificationService.create_notification(
                user=staff,
                notification_type='staff_cancellation',
                channel='email',  # Dla obsługi zawsze email
                context=context,
                related_obj=reservation
            )
    
    @staticmethod
    def send_staff_new_booking_notification(reservation):
        """Powiadamia obsługę o nowej rezerwacji"""
        staff_users = User.objects.filter(groups__name='Staff').distinct()
        
        for staff in staff_users:
            context = {
                'user': staff,
                'reservation': reservation,
                'client': reservation.user,
                'service': reservation.service,
                'subject': f'Nowa rezerwacja - {reservation.service.name}',
            }
            
            NotificationService.create_notification(
                user=staff,
                notification_type='staff_new_booking',
                channel='email',
                context=context,
                related_obj=reservation
            )
    
    @staticmethod
    def _get_cancellation_url(reservation):
        """Generuje URL do odwołania wizyty"""
        # Upewnij się że token istnieje
        if not reservation.cancellation_token:
            reservation.generate_cancellation_token()
        
        from django.urls import reverse
        try:
            return reverse('cancel_booking_token', kwargs={'token': reservation.cancellation_token})
        except Exception:
            return '#'


class EmailBackend:
    """Backend do wysyłania e-maili"""
    
    @staticmethod
    def send(notification):
        """
        Wysyła e-mail
        
        Args:
            notification: Notification object
        
        Returns:
            bool: True jeśli sukces, False jeśli błąd
        """
        try:
            if notification.html_message:
                # Wyślij z HTML
                email = EmailMultiAlternatives(
                    subject=notification.subject,
                    body=notification.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[notification.recipient]
                )
                email.attach_alternative(notification.html_message, "text/html")
                email.send(fail_silently=False)
            else:
                # Zwykły tekst
                send_mail(
                    subject=notification.subject,
                    message=notification.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notification.recipient],
                    fail_silently=False
                )
            
            notification.mark_sent()
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed for notification {notification.id}: {e}")
            notification.mark_failed(str(e))
            return False


class SMSBackend:
    """Backend do wysyłania SMS (integracja z Twilio/SMSApi)"""
    
    @staticmethod
    def send(notification):
        """
        Wysyła SMS
        
        Args:
            notification: Notification object
        
        Returns:
            bool: True jeśli sukces, False jeśli błąd
        """
        # W MVP - loguj do konsoli
        # W produkcji - integracja z Twilio lub SMSApi
        
        try:
            # Sprawdź czy Twilio skonfigurowane
            if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
                return SMSBackend._send_via_twilio(notification)
            else:
                # MVP - loguj do konsoli
                logger.info(f"[SMS MVP] To: {notification.recipient}")
                logger.info(f"[SMS MVP] Message: {notification.message}")
                notification.mark_sent()
                return True
                
        except Exception as e:
            logger.error(f"SMS sending failed for notification {notification.id}: {e}")
            notification.mark_failed(str(e))
            return False
    
    @staticmethod
    def _send_via_twilio(notification):
        """Wysyła SMS przez Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            message = client.messages.create(
                body=notification.message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=notification.recipient
            )
            
            notification.mark_sent()
            logger.info(f"SMS sent via Twilio, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            raise
