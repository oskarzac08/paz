"""
Celery tasks dla systemu powiadomień

Zgodnie z ADR-007 i PDR-007
"""

from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id):
    """
    Wysyła powiadomienie asynchronicznie
    
    Args:
        notification_id: ID powiadomienia do wysłania
    
    Returns:
        str: Status wysyłki
    """
    from .models import Notification
    from .notification_service import EmailBackend, SMSBackend
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Sprawdź czy już wysłane
        if notification.status == 'sent':
            return f"Notification {notification_id} already sent"
        
        # Wybierz backend i wyślij
        if notification.channel == 'email':
            backend = EmailBackend()
            success = backend.send(notification)
        elif notification.channel == 'sms':
            backend = SMSBackend()
            success = backend.send(notification)
        else:
            raise ValueError(f"Unknown channel: {notification.channel}")
        
        if success:
            logger.info(f"Notification {notification_id} sent successfully")
            return f"Notification {notification_id} sent"
        else:
            raise Exception("Backend returned False")
            
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return f"Notification {notification_id} not found"
    
    except Exception as exc:
        # Zwiększ licznik ponowień
        notification.retry_count += 1
        notification.error_message = str(exc)
        notification.save()
        
        logger.warning(f"Notification {notification_id} failed (attempt {notification.retry_count}): {exc}")
        
        # Retry z exponential backoff
        if notification.retry_count < 3:
            raise self.retry(exc=exc, countdown=60 * (2 ** notification.retry_count))
        else:
            notification.mark_failed(f"Failed after 3 retries: {exc}")
            logger.error(f"Notification {notification_id} failed permanently after 3 retries")
            return f"Notification {notification_id} failed permanently"


@shared_task
def send_daily_reminders_24h():
    """
    Wysyła przypomnienia o wizytach za 24h
    Uruchamiany codziennie o 10:00
    """
    from .models import Reservation
    from .notification_service import NotificationService
    
    # Znajdź wizyty za ~24h (okno: 23-25h)
    now = timezone.now()
    tomorrow_start = now + timedelta(hours=23)
    tomorrow_end = now + timedelta(hours=25)
    
    upcoming_reservations = Reservation.objects.filter(
        status__in=['pending', 'confirmed'],
        start__gte=tomorrow_start,
        start__lt=tomorrow_end,
        user__isnull=False  # Tylko dla zarejestrowanych użytkowników
    ).select_related('user', 'service')
    
    sent_count = 0
    for reservation in upcoming_reservations:
        try:
            notification = NotificationService.send_booking_reminder(reservation, hours_before=24)
            if notification:
                sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send 24h reminder for reservation {reservation.id}: {e}")
    
    logger.info(f"Sent {sent_count} 24h reminders (out of {upcoming_reservations.count()} reservations)")
    return f"Sent {sent_count}/{upcoming_reservations.count()} 24h reminders"


@shared_task
def send_reminders_2h():
    """
    Wysyła przypomnienia o wizytach za 2h
    Uruchamiany co godzinę (sprawdza wizyty za 1.5-2.5h)
    """
    from .models import Reservation
    from .notification_service import NotificationService
    
    # Znajdź wizyty za ~2h (okno: 1.5-2.5h)
    now = timezone.now()
    reminder_start = now + timedelta(hours=1, minutes=30)
    reminder_end = now + timedelta(hours=2, minutes=30)
    
    upcoming_reservations = Reservation.objects.filter(
        status__in=['pending', 'confirmed'],
        start__gte=reminder_start,
        start__lt=reminder_end,
        user__isnull=False
    ).select_related('user', 'service')
    
    sent_count = 0
    for reservation in upcoming_reservations:
        try:
            # Sprawdź czy użytkownik ma włączone przypomnienia 2h
            if hasattr(reservation.user, 'notification_preferences'):
                if not reservation.user.notification_preferences.enable_reminder_2h:
                    continue
            
            notification = NotificationService.send_booking_reminder(reservation, hours_before=2)
            if notification:
                sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send 2h reminder for reservation {reservation.id}: {e}")
    
    logger.info(f"Sent {sent_count} 2h reminders (out of {upcoming_reservations.count()} reservations)")
    return f"Sent {sent_count}/{upcoming_reservations.count()} 2h reminders"


@shared_task
def send_staff_daily_report():
    """
    Wysyła raport dzienny dla obsługi
    Uruchamiany codziennie o 8:00
    """
    from .models import Reservation, Notification
    from .notification_service import NotificationService
    
    # Znajdź wizyty na dziś
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = today_start + timedelta(days=1)
    
    today_reservations = Reservation.objects.filter(
        start__gte=today_start,
        start__lt=today_end,
        status__in=['pending', 'confirmed']
    ).select_related('user', 'service').order_by('start')
    
    # Przygotuj raport
    report_lines = [
        f"Raport dzienny - {today.strftime('%d.m.Y')}",
        f"",
        f"Liczba wizyt na dziś: {today_reservations.count()}",
        f"",
    ]
    
    if today_reservations.exists():
        report_lines.append("Lista wizyt:")
        report_lines.append("─" * 50)
        
        for res in today_reservations:
            client_name = res.user.get_full_name() if res.user else res.customer_email
            report_lines.append(
                f"{res.start.strftime('%H:%M')} - {res.service.name} - {client_name}"
            )
            if res.customer_phone:
                report_lines.append(f"  Tel: {res.customer_phone}")
            if res.notes:
                report_lines.append(f"  Uwagi: {res.notes}")
            report_lines.append("")
    else:
        report_lines.append("Brak wizyt na dziś.")
    
    report_text = "\n".join(report_lines)
    
    # Wyślij do wszystkich pracowników z grupy Staff
    staff_users = User.objects.filter(groups__name='Staff').distinct()
    
    sent_count = 0
    for staff in staff_users:
        try:
            context = {
                'user': staff,
                'subject': f'Raport dzienny - {today.strftime("%d.m.%Y")}',
                'message': report_text,
                'reservations': today_reservations,
                'date': today,
            }
            
            notification = NotificationService.create_notification(
                user=staff,
                notification_type='staff_daily_report',
                channel='email',
                context=context
            )
            
            if notification:
                sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send daily report to staff {staff.id}: {e}")
    
    logger.info(f"Sent daily report to {sent_count} staff members")
    return f"Sent daily report to {sent_count} staff members"


@shared_task
def send_staff_weekly_report():
    """
    Wysyła raport tygodniowy dla obsługi
    Uruchamiany w poniedziałki o 9:00
    """
    from .models import Reservation
    from .notification_service import NotificationService
    
    # Znajdź wizyty z ostatniego tygodnia
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    week_start = timezone.make_aware(timezone.datetime.combine(week_ago, timezone.datetime.min.time()))
    week_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    # Statystyki
    total_reservations = Reservation.objects.filter(
        created_at__gte=week_start,
        created_at__lt=week_end
    ).count()
    
    completed = Reservation.objects.filter(
        created_at__gte=week_start,
        created_at__lt=week_end,
        status='completed'
    ).count()
    
    cancelled = Reservation.objects.filter(
        created_at__gte=week_start,
        created_at__lt=week_end,
        status='cancelled'
    ).count()
    
    no_show = Reservation.objects.filter(
        created_at__gte=week_start,
        created_at__lt=week_end,
        status='no_show'
    ).count()
    
    # Przygotuj raport
    report_lines = [
        f"Raport tygodniowy - {week_ago.strftime('%d.m.Y')} - {today.strftime('%d.m.Y')}",
        f"",
        f"Statystyki:",
        f"  Wszystkie rezerwacje: {total_reservations}",
        f"  Zrealizowane: {completed}",
        f"  Odwołane: {cancelled}",
        f"  No-show: {no_show}",
        f"",
    ]
    
    if total_reservations > 0:
        completion_rate = (completed / total_reservations) * 100
        cancellation_rate = (cancelled / total_reservations) * 100
        no_show_rate = (no_show / total_reservations) * 100
        
        report_lines.append(f"Wskaźniki:")
        report_lines.append(f"  Realizacja: {completion_rate:.1f}%")
        report_lines.append(f"  Odwołania: {cancellation_rate:.1f}%")
        report_lines.append(f"  No-show: {no_show_rate:.1f}%")
    
    report_text = "\n".join(report_lines)
    
    # Wyślij do obsługi
    staff_users = User.objects.filter(groups__name='Staff').distinct()
    
    sent_count = 0
    for staff in staff_users:
        try:
            context = {
                'user': staff,
                'subject': f'Raport tygodniowy - {week_ago.strftime("%d.m")} - {today.strftime("%d.m.%Y")}',
                'message': report_text,
                'total_reservations': total_reservations,
                'completed': completed,
                'cancelled': cancelled,
                'no_show': no_show,
            }
            
            notification = NotificationService.create_notification(
                user=staff,
                notification_type='staff_weekly_report',
                channel='email',
                context=context
            )
            
            if notification:
                sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send weekly report to staff {staff.id}: {e}")
    
    logger.info(f"Sent weekly report to {sent_count} staff members")
    return f"Sent weekly report to {sent_count} staff members"


@shared_task
def cleanup_old_notifications():
    """
    Usuwa stare powiadomienia (starsze niż 90 dni)
    Uruchamiany w poniedziałki o 2:00
    """
    from .models import Notification
    
    threshold = timezone.now() - timedelta(days=90)
    
    deleted_count, _ = Notification.objects.filter(
        created_at__lt=threshold
    ).delete()
    
    logger.info(f"Deleted {deleted_count} old notifications")
    return f"Deleted {deleted_count} old notifications"


@shared_task
def retry_failed_notifications():
    """
    Ponawia wysyłkę nieudanych powiadomień (max 24h old)
    Uruchamiany co 6 godzin
    """
    from .models import Notification
    
    # Znajdź nieudane powiadomienia młodsze niż 24h z mniej niż 3 próbami
    threshold = timezone.now() - timedelta(hours=24)
    
    failed_notifications = Notification.objects.filter(
        status='failed',
        created_at__gte=threshold,
        retry_count__lt=3
    )
    
    retry_count = 0
    for notification in failed_notifications:
        try:
            # Resetuj status
            notification.status = 'pending'
            notification.save()
            
            # Wyślij ponownie
            send_notification_task.delay(notification.id)
            retry_count += 1
        except Exception as e:
            logger.error(f"Failed to retry notification {notification.id}: {e}")
    
    logger.info(f"Retried {retry_count} failed notifications")
    return f"Retried {retry_count} failed notifications"
