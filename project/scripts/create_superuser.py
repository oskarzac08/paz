import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','project.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username='admin'
password='adminpass'
email='admin@example.com'
user, created = User.objects.get_or_create(username=username, defaults={'email':email,'is_staff':True,'is_superuser':True})
if created:
    user.set_password(password)
    user.save()
    print('Utworzono superużytkownika admin')
else:
    user.set_password(password)
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print('Zaktualizowano istniejącego użytkownika admin')
from ideas.models import Idea, Reservation
from django.utils import timezone
now = timezone.now()
# Przykładowe pomysły
Idea.objects.get_or_create(title='Pierwszy pomysł', defaults={'description':'Opis pierwszego pomysłu'})
Idea.objects.get_or_create(title='Drugi pomysł', defaults={'description':'Opis drugiego pomysłu'})
# Przykładowe rezerwacje
Reservation.objects.get_or_create(name='Rezerwacja A', defaults={'start_time': now, 'end_time': now + timezone.timedelta(hours=1)})
Reservation.objects.get_or_create(name='Rezerwacja B', defaults={'start_time': now + timezone.timedelta(days=1), 'end_time': now + timezone.timedelta(days=1, hours=2)})
print('Dodano przykładowe Idea i Reservation')
