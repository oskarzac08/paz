"""
Celery configuration for project

Zgodnie z ADR-007
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

# Load configuration from Django settings, with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Periodic tasks schedule (Celery Beat)
app.conf.beat_schedule = {
    # Przypomnienia 24h przed wizytą - codziennie o 10:00
    'send-24h-reminders': {
        'task': 'ideas.notification_tasks.send_daily_reminders_24h',
        'schedule': crontab(hour=10, minute=0),
    },
    
    # Przypomnienia 2h przed wizytą - co godzinę
    'send-2h-reminders': {
        'task': 'ideas.notification_tasks.send_reminders_2h',
        'schedule': crontab(minute=0),  # Co godzinę o pełnej godzinie
    },
    
    # Raport dzienny dla obsługi - codziennie o 8:00
    'send-staff-daily-report': {
        'task': 'ideas.notification_tasks.send_staff_daily_report',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Raport tygodniowy dla obsługi - poniedziałki o 9:00
    'send-staff-weekly-report': {
        'task': 'ideas.notification_tasks.send_staff_weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    
    # Czyszczenie starych powiadomień - poniedziałki o 2:00
    'cleanup-old-notifications': {
        'task': 'ideas.notification_tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
    },
    
    # Ponowienie nieudanych powiadomień - co 6h
    'retry-failed-notifications': {
        'task': 'ideas.notification_tasks.retry_failed_notifications',
        'schedule': crontab(hour='*/6', minute=0),
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Warsaw',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')
