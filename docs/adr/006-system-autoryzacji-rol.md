# ADR-006: System autoryzacji i ról użytkowników

## Status

Zaakceptowany

## Kontekst

System wymaga rozróżnienia między dwoma typami użytkowników:

### Klient (Client)

- Przeglądanie usług i dostępnych terminów
- Rezerwowanie wizyt
- Zarządzanie własnymi rezerwacjami
- Odwoływanie wizyt (z ograniczeniami)
- Podgląd historii wizyt

### Obsługa (Staff)

- Wszystkie uprawnienia klienta
- Tworzenie i zarządzanie usługami
- Tworzenie terminów (pojedyncze i cykliczne)
- Rezerwowanie wizyt w imieniu klientów
- Wyszukiwanie klientów
- Tworzenie kont klientów
- Odwoływanie i edycja rezerwacji klientów
- Pełny dostęp do panelu administracyjnego

### Wymagania bezpieczeństwa

- Separacja uprawnień między klientami a obsługą
- Klienci mogą zarządzać tylko swoimi rezerwacjami
- Obsługa ma dostęp do wszystkich danych
- Audyt operacji (kto, kiedy, co zrobił)

## Decyzja

Wykorzystujemy wbudowany system uprawnień Django z grupami i permission:

### 1. Role użytkowników oparte na Django Groups

```python
# accounts/roles.py

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class UserRoles:
    CLIENT = 'Client'
    STAFF = 'Staff'
    MANAGER = 'Manager'  # przyszła rola

def setup_groups():
    """
    Setup grup użytkowników z odpowiednimi uprawnieniami.
    Wywołaj w migrations lub management command.
    """
    
    # Grupa: Client (podstawowe uprawnienia)
    client_group, _ = Group.objects.get_or_create(name=UserRoles.CLIENT)
    client_permissions = [
        'view_service',
        'view_timeslot',
        'add_booking',
        'view_booking',
        'change_booking',  # tylko swoje
        'delete_booking',  # tylko swoje (anulowanie)
    ]
    assign_permissions(client_group, client_permissions)
    
    # Grupa: Staff (pełne uprawnienia)
    staff_group, _ = Group.objects.get_or_create(name=UserRoles.STAFF)
    staff_permissions = [
        # Service management
        'add_service',
        'change_service',
        'delete_service',
        'view_service',
        'add_serviceimage',
        'change_serviceimage',
        'delete_serviceimage',
        'view_serviceimage',
        
        # TimeSlot management
        'add_timeslot',
        'change_timeslot',
        'delete_timeslot',
        'view_timeslot',
        
        # Booking management (wszystkie)
        'add_booking',
        'change_booking',
        'delete_booking',
        'view_booking',
        
        # User management
        'view_user',
        'view_userprofile',
        'change_userprofile',
    ]
    assign_permissions(staff_group, staff_permissions)

def assign_permissions(group, permission_codenames):
    """Przypisuje uprawnienia do grupy"""
    permissions = Permission.objects.filter(codename__in=permission_codenames)
    group.permissions.set(permissions)
```

### 2. Custom User Manager

```python
# accounts/managers.py

from django.contrib.auth.models import UserManager as BaseUserManager

class UserManager(BaseUserManager):
    
    def create_client(self, email, phone_number, first_name, last_name, password=None):
        """Tworzy użytkownika z rolą klienta"""
        user = self.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Dodaj do grupy Client
        client_group = Group.objects.get(name=UserRoles.CLIENT)
        user.groups.add(client_group)
        
        # Utwórz profil
        UserProfile.objects.create(
            user=user,
            phone_number=phone_number
        )
        
        return user
    
    def create_staff_user(self, email, first_name, last_name, password):
        """Tworzy użytkownika obsługi"""
        user = self.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_staff=True
        )
        
        # Dodaj do grupy Staff
        staff_group = Group.objects.get(name=UserRoles.STAFF)
        user.groups.add(staff_group)
        
        return user
```

### 3. Permission Mixins dla Views

```python
# core/mixins.py

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class StaffRequiredMixin(UserPassesTestMixin):
    """Wymaga aby użytkownik był w grupie Staff"""
    
    def test_func(self):
        return self.request.user.groups.filter(name=UserRoles.STAFF).exists()

class OwnerOrStaffRequiredMixin(UserPassesTestMixin):
    """Wymaga aby użytkownik był właścicielem obiektu lub staff"""
    
    def test_func(self):
        obj = self.get_object()
        
        # Staff ma dostęp do wszystkiego
        if self.request.user.groups.filter(name=UserRoles.STAFF).exists():
            return True
        
        # Sprawdź czy użytkownik jest właścicielem
        return self.is_owner(obj)
    
    def is_owner(self, obj):
        """Override w konkretnych widokach"""
        raise NotImplementedError("Zaimplementuj metodę is_owner")

class BookingOwnerMixin(OwnerOrStaffRequiredMixin):
    """Mixin dla widoków rezerwacji"""
    
    def is_owner(self, obj):
        return obj.client == self.request.user
```

### 4. Przykładowe Views z permissions

```python
# bookings/views.py

class ServiceListView(LoginRequiredMixin, ListView):
    """Lista usług - dostępna dla wszystkich"""
    model = Service
    queryset = Service.objects.filter(is_active=True)

class ServiceCreateView(StaffRequiredMixin, CreateView):
    """Tworzenie usługi - tylko staff"""
    model = Service
    form_class = ServiceForm
    permission_denied_message = "Tylko obsługa może tworzyć usługi"

class BookingDetailView(BookingOwnerMixin, DetailView):
    """Szczegóły rezerwacji - właściciel lub staff"""
    model = Booking

class BookingCancelView(BookingOwnerMixin, View):
    """Anulowanie rezerwacji - właściciel lub staff"""
    
    def post(self, request, pk):
        booking = self.get_object()
        
        # Logika anulowania z audytem
        try:
            BookingService.cancel_booking(
                booking=booking,
                cancelled_by=request.user
            )
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('booking_list')

class StaffBookingCreateView(StaffRequiredMixin, CreateView):
    """Tworzenie rezerwacji przez staff w imieniu klienta"""
    model = Booking
    template_name = 'bookings/staff_booking_create.html'
    
    def form_valid(self, form):
        # Staff wybiera klienta z listy
        client_id = self.request.POST.get('client_id')
        client = User.objects.get(id=client_id)
        
        booking = BookingService.create_booking(
            client=client,
            time_slot_id=form.cleaned_data['time_slot'].id,
            terms_accepted=True
        )
        
        # Audyt
        booking.created_by = self.request.user
        booking.save()
        
        return redirect('booking_detail', pk=booking.pk)
```

### 5. Template permissions

```django
<!-- templates/base.html -->
{% load auth_extras %}

<nav>
    <a href="{% url 'service_list' %}">Usługi</a>
    <a href="{% url 'my_bookings' %}">Moje wizyty</a>
    
    {% if request.user|has_group:"Staff" %}
    <a href="{% url 'staff_dashboard' %}">Panel obsługi</a>
    <a href="{% url 'service_create' %}">Dodaj usługę</a>
    <a href="{% url 'timeslot_create' %}">Zarządzaj terminami</a>
    {% endif %}
    
    {% if user.is_staff %}
    <a href="{% url 'admin:index' %}">Admin</a>
    {% endif %}
</nav>
```

### 6. Custom template tag

```python
# accounts/templatetags/auth_extras.py

from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """Sprawdza czy użytkownik jest w grupie"""
    return user.groups.filter(name=group_name).exists()

@register.filter(name='is_staff_member')
def is_staff_member(user):
    """Sprawdza czy użytkownik jest w grupie Staff"""
    return user.groups.filter(name='Staff').exists()
```

### 7. QuerySet filtering based on role

```python
# bookings/managers.py

class BookingQuerySet(models.QuerySet):
    
    def for_user(self, user):
        """Zwraca rezerwacje dostępne dla użytkownika"""
        if user.groups.filter(name=UserRoles.STAFF).exists():
            # Staff widzi wszystko
            return self.all()
        else:
            # Klient widzi tylko swoje
            return self.filter(client=user)

class BookingManager(models.Manager):
    def get_queryset(self):
        return BookingQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)

# W modelu
class Booking(models.Model):
    # ... fields
    objects = BookingManager()
```

### 8. Audyt działań

```python
# core/models.py

class AuditLog(models.Model):
    """Model do logowania działań użytkowników"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # 'create', 'update', 'delete', 'cancel'
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    changes = models.JSONField(default=dict)  # szczegóły zmian
    ip_address = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

# Middleware dla audytu
class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log akcji modyfikujących
        if request.method in ['POST', 'PUT', 'DELETE'] and request.user.is_authenticated:
            # Implementacja logowania
            pass
        
        return response
```

## Uzasadnienie

### Dlaczego Django Groups zamiast custom roles?

- **Built-in**: Wykorzystanie wbudowanych mechanizmów Django
- **Admin integration**: Zarządzanie przez Django admin
- **Permissions**: Integracja z systemem permissions
- **Extensibility**: Łatwe dodawanie nowych ról

### Dlaczego mixins dla views?

- **DRY**: Reużywalny kod
- **Clarity**: Czytelne wymagania uprawnień
- **Centralization**: Logika autoryzacji w jednym miejscu

### Dlaczego audyt?

- **Compliance**: Wymogi prawne (RODO)
- **Security**: Śledzenie podejrzanych działań
- **Debug**: Pomoc w rozwiązywaniu problemów

## Konsekwencje

### Pozytywne

- Wykorzystanie sprawdzonych mechanizmów Django
- Granularna kontrola uprawnień
- Łatwe zarządzanie rolami przez admin
- Bezpieczna separacja dostępu
- Audyt wszystkich operacji

### Negatywne

- Więcej boilerplate w views (mixins)
- Trzeba pamiętać o sprawdzaniu uprawnień
- QuerySet filtering może być mylący
- Audyt generuje dużo danych

### Security considerations

```python
# settings.py

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

## Implementacja

### Migration dla grup

```python
# accounts/migrations/0002_setup_groups.py

from django.db import migrations

def create_groups(apps, schema_editor):
    from accounts.roles import setup_groups
    setup_groups()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('bookings', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(create_groups),
    ]
```

### Management command

```bash
python manage.py setup_permissions
```

```python
# accounts/management/commands/setup_permissions.py

from django.core.management.base import BaseCommand
from accounts.roles import setup_groups

class Command(BaseCommand):
    help = 'Setup user groups and permissions'
    
    def handle(self, *args, **options):
        setup_groups()
        self.stdout.write(self.style.SUCCESS('Groups and permissions created'))
```

## Alternatywy rozważone

1. **django-guardian (object-level permissions)** - Overkill dla obecnych potrzeb
2. **Własny model Role** - Reinventing the wheel
3. **JWT tokens z rolami** - Bardziej dla API niż web app
4. **Casbin** - Too complex

## Odniesienia

- Django Authentication: <https://docs.djangoproject.com/en/stable/topics/auth/>
- Django Permissions: <https://docs.djangoproject.com/en/stable/topics/auth/default/#permissions-and-authorization>
- Django Groups: <https://docs.djangoproject.com/en/stable/topics/auth/default/#groups>
- User Authentication in Django: <https://docs.djangoproject.com/en/stable/topics/auth/customizing/>
