"""
Konfiguracja pytest dla projektu Django
"""
import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Konfiguracja bazy danych dla testów"""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatyczny dostęp do bazy danych dla wszystkich testów"""
    pass
