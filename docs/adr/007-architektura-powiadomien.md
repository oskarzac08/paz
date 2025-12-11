# ADR-007: Architektura powiadomień

## Status

Zaakceptowany

## Kontekst

System wymaga wysyłania powiadomień użytkownikom w różnych scenariuszach:

### Dla klienta

- Potwierdzenie rejestracji (e-mail/SMS z kodem weryfikacyjnym)
- Potwierdzenie rezerwacji wizyty
- Przypomnienie o nadchodzącej wizycie (24h przed)
- Powiadomienie o odwołaniu wizyty
- Powiadomienie o zmianach w wizycie

### Dla obsługi

- Powiadomienie o nowej rezerwacji
- Powiadomienie o odwołaniu wizyty przez klienta
- Alert o brakujących terminach
- Raport dzienny/tygodniowy

### Wymagania

- Wsparcie dla wielu kanałów (e-mail, SMS)
- Możliwość wyboru preferowanego kanału przez użytkownika
- Asynchroniczne wysyłanie (nie blokować requesta)
- Retry mechanism dla nieudanych wysyłek
- Template system dla wiadomości
- Tracking statusu wysyłki

## Decyzja

Implementujemy system powiadomień oparty na Celery z następującymi komponentami:

### 1. Model dla powiadomień

```python
# notifications/models.py

from django.db import models
from django.conf import settings

class Notification(models.Model):
    """Model przechowujący historię wysłanych powiadomień"""
    
    CHANNEL_CHOICES = [
        ('email', 'E-mail'),
        ('sms', 'SMS'),
        ('push', 'Push notification'),  # przyszła funkcjonalność
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Oczekujące'),
        ('sent', 'Wysłane'),
        ('failed', 'Nieudane'),
        ('cancelled', 'Anulowane'),
    ]
    
    TYPE_CHOICES = [
        ('verification_code', 'Kod weryfikacyjny'),
        ('booking_confirmation', 'Potwierdzenie rezerwacji'),
        ('booking_reminder', 'Przypomnienie o wizycie'),
        ('booking_cancelled', 'Odwołanie wizyty'),
        ('booking_modified', 'Zmiana w wizycie'),
        ('staff_alert', 'Alert dla obsługi'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255)  # email lub numer telefonu
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    related_object_type = models.CharField(max_length=50, blank=True)  # 'Booking', 'ActivationCode'
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} -> {self.recipient} ({self.status})"
```

### 2. Notification Service

```python
# notifications/services.py

from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

class NotificationService:
    
    @staticmethod
    def create_notification(user, notification_type, channel, context=None, related_obj=None):
        """
        Tworzy powiadomienie i wysyła je asynchronicznie
        
        Args:
            user: Użytkownik
            notification_type: Typ powiadomienia
            channel: Kanał ('email' lub 'sms')
            context: Dane do template
            related_obj: Powiązany obiekt (Booking, ActivationCode, etc.)
        """
        from .tasks import send_notification_task
        
        # Określ odbiorcę na podstawie kanału
        if channel == 'email':
            recipient = user.email
        elif channel == 'sms':
            recipient = user.profile.phone_number
        else:
            raise ValueError(f"Unsupported channel: {channel}")
        
        # Renderuj message z template
        template_name = f'notifications/{notification_type}_{channel}.txt'
        message = render_to_string(template_name, context or {})
        
        # Dla email, opcjonalnie HTML
        subject = ''
        if channel == 'email':
            subject = context.get('subject', f'Powiadomienie - {notification_type}')
        
        # Utwórz notification
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            message=message,
            related_object_type=type(related_obj).__name__ if related_obj else '',
            related_object_id=related_obj.id if related_obj else None,
        )
        
        # Wyślij asynchronicznie przez Celery
        send_notification_task.delay(notification.id)
        
        return notification
    
    @staticmethod
    def send_booking_confirmation(booking):
        """Wysyła potwierdzenie rezerwacji"""
        user = booking.client
        channel = user.profile.preferred_contact
        
        context = {
            'user': user,
            'booking': booking,
            'service': booking.service,
            'time_slot': booking.time_slot,
            'subject': f'Potwierdzenie rezerwacji - {booking.service.name}',
        }
        
        return NotificationService.create_notification(
            user=user,
            notification_type='booking_confirmation',
            channel=channel,
            context=context,
            related_obj=booking
        )
    
    @staticmethod
    def send_booking_reminder(booking, hours_before=24):
        """Wysyła przypomnienie o wizycie"""
        user = booking.client
        channel = user.profile.preferred_contact
        
        context = {
            'user': user,
            'booking': booking,
            'service': booking.service,
            'time_slot': booking.time_slot,
            'hours_before': hours_before,
            'subject': f'Przypomnienie o wizycie - {booking.service.name}',
        }
        
        return NotificationService.create_notification(
            user=user,
            notification_type='booking_reminder',
            channel=channel,
            context=context,
            related_obj=booking
        )
    
    @staticmethod
    def send_cancellation_notification(booking, cancelled_by):
        """Powiadamia o odwołaniu wizyty"""
        # Powiadom klienta
        context = {
            'user': booking.client,
            'booking': booking,
            'cancelled_by': cancelled_by,
            'subject': f'Wizyta odwołana - {booking.service.name}',
        }
        
        client_notification = NotificationService.create_notification(
            user=booking.client,
            notification_type='booking_cancelled',
            channel=booking.client.profile.preferred_contact,
            context=context,
            related_obj=booking
        )
        
        # Powiadom obsługę (jeśli klient odwołał)
        if cancelled_by == booking.client:
            # Wyślij powiadomienie do staff
            staff_users = User.objects.filter(groups__name='Staff')
            for staff in staff_users:
                NotificationService.create_notification(
                    user=staff,
                    notification_type='staff_alert',
                    channel='email',
                    context={
                        'booking': booking,
                        'client': booking.client,
                        'subject': f'Klient odwołał wizytę - {booking.service.name}',
                    },
                    related_obj=booking
                )
        
        return client_notification
```

### 3. Celery Tasks

```python
# notifications/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    """
    Wysyła powiadomienie asynchronicznie
    """
    from .models import Notification
    from .backends import EmailBackend, SMSBackend
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Sprawdź czy już wysłane
        if notification.status == 'sent':
            return f"Notification {notification_id} already sent"
        
        # Wybierz backend
        if notification.channel == 'email':
            backend = EmailBackend()
            success = backend.send(
                recipient=notification.recipient,
                subject=notification.subject,
                message=notification.message
            )
        elif notification.channel == 'sms':
            backend = SMSBackend()
            success = backend.send(
                phone_number=notification.recipient,
                message=notification.message
            )
        else:
            raise ValueError(f"Unknown channel: {notification.channel}")
        
        # Aktualizuj status
        if success:
            notification.status = 'sent'
            notification.sent_at = timezone.now()
            notification.save()
            logger.info(f"Notification {notification_id} sent successfully")
        else:
            raise Exception("Backend returned False")
            
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return f"Notification {notification_id} not found"
    
    except Exception as exc:
        notification.retry_count += 1
        notification.error_message = str(exc)
        notification.save()
        
        logger.warning(f"Notification {notification_id} failed: {exc}")
        
        # Retry z exponential backoff
        if notification.retry_count < 3:
            raise self.retry(exc=exc, countdown=60 * (2 ** notification.retry_count))
        else:
            notification.status = 'failed'
            notification.save()
            logger.error(f"Notification {notification_id} failed after 3 retries")


@shared_task
def send_daily_reminders():
    """
    Wysyła przypomnienia o wizytach za 24h
    Uruchamiany codziennie o określonej godzinie
    """
    from bookings.models import Booking
    from datetime import timedelta
    
    tomorrow = timezone.now() + timedelta(hours=24)
    tomorrow_end = tomorrow + timedelta(hours=1)
    
    # Znajdź wizyty za ~24h
    upcoming_bookings = Booking.objects.filter(
        status='scheduled',
        time_slot__start_datetime__gte=tomorrow,
        time_slot__start_datetime__lt=tomorrow_end
    ).select_related('client', 'service', 'time_slot')
    
    for booking in upcoming_bookings:
        NotificationService.send_booking_reminder(booking)
    
    logger.info(f"Sent {upcoming_bookings.count()} reminders")
    return f"Sent {upcoming_bookings.count()} reminders"
```

### 4. Backends

```python
# notifications/backends.py

from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailBackend:
    """Backend do wysyłania e-maili"""
    
    def send(self, recipient, subject, message, html_message=None):
        """
        Wysyła e-mail
        
        Returns:
            bool: True jeśli sukces, False jeśli błąd
        """
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False

class SMSBackend:
    """Backend do wysyłania SMS (integracja z Twilio/SMSApi)"""
    
    def send(self, phone_number, message):
        """
        Wysyła SMS
        
        Returns:
            bool: True jeśli sukces, False jeśli błąd
        """
        # Przykład dla Twilio
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            return True
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
```

### 5. Templates dla powiadomień

```django
<!-- notifications/templates/notifications/booking_confirmation_email.txt -->
Witaj {{ user.first_name }},

Twoja rezerwacja została potwierdzona!

Usługa: {{ service.name }}
Data: {{ time_slot.start_datetime|date:"d.m.Y" }}
Godzina: {{ time_slot.start_datetime|time:"H:i" }}
Czas trwania: {{ service.duration }}

W razie pytań, skontaktuj się z nami.

Pozdrawiamy,
Zespół {{ site_name }}
```

```django
<!-- notifications/templates/notifications/booking_reminder_sms.txt -->
Przypomnienie: Wizyta {{ service.name }} jutro o {{ time_slot.start_datetime|time:"H:i" }}. Do zobaczenia!
```

### 6. Celery Configuration

```python
# project/celery.py

from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'notifications.tasks.send_daily_reminders',
        'schedule': crontab(hour=10, minute=0),  # Codziennie o 10:00
    },
    'cleanup-old-notifications': {
        'task': 'notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Poniedziałki o 2:00
    },
}
```

### 7. Settings

```python
# settings.py

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@booking-system.com'

# SMS configuration (Twilio)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Warsaw'
```

## Uzasadnienie

### Dlaczego Celery?

- **Asynchronous**: Nie blokuje HTTP requestów
- **Reliability**: Retry mechanism, persistence
- **Scalability**: Możliwość dodania workerów
- **Scheduling**: Periodic tasks (reminders)

### Dlaczego osobny model Notification?

- **Auditing**: Historia wszystkich wysłanych powiadomień
- **Debugging**: Śledzenie błędów wysyłki
- **Analytics**: Statystyki powiadomień
- **Compliance**: RODO - tracking komunikacji

### Dlaczego template system?

- **Flexibility**: Łatwa edycja treści bez kodu
- **Localization**: Przyszłe wsparcie dla wielu języków
- **Consistency**: Jednolity wygląd powiadomień

## Konsekwencje

### Pozytywne

- Niezawodna wysyłka powiadomień
- Retry mechanism dla błędów
- Historia wszystkich powiadomień
- Łatwe dodawanie nowych typów powiadomień
- Scheduled tasks dla przypomnień

### Negatywne

- Wymaga Redis/RabbitMQ dla Celery
- Dodatkowa złożoność infrastruktury
- Koszty wysyłki SMS
- Monitoring Celery workers

### Monitoring

```python
# Flower dla monitoringu Celery
pip install flower
celery -A project flower
```

## Implementacja

### Uruchomienie Celery

```bash
# Worker
celery -A project worker -l info

# Beat (scheduler)
celery -A project beat -l info

# Razem (development)
celery -A project worker -B -l info
```

### Cleanup task

```python
@shared_task
def cleanup_old_notifications():
    """Usuń powiadomienia starsze niż 90 dni"""
    threshold = timezone.now() - timedelta(days=90)
    deleted = Notification.objects.filter(
        created_at__lt=threshold
    ).delete()
    logger.info(f"Deleted {deleted[0]} old notifications")
```

## Alternatywy rozważone

1. **Django Channels + WebSockets** - Dla real-time, ale overkill dla e-mail/SMS
2. **External services (SendGrid, Mailgun)** - Możliwe w przyszłości
3. **Synchronous sending** - Blokuje requesty, zła UX
4. **Database queue** - Mniej niezawodne niż Celery+Redis

## Odniesienia

- Celery Documentation: <https://docs.celeryq.dev/>
- Django Email: <https://docs.djangoproject.com/en/stable/topics/email/>
- Twilio Python: <https://www.twilio.com/docs/libraries/python>
- Flower: <https://flower.readthedocs.io/>
