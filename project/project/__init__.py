"""
Django project initialization
"""

# This will make sure the Celery app is always imported when
# Django starts so that shared_task will use this app.
# Celery is optional for MVP - graceful fallback if not installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed - notifications will work synchronously
    pass
