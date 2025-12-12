# ADR-002: Architektura modeli danych

## Status

Zaakceptowany

## Kontekst

Zgodnie z wymaganiami biznesowymi (docs/technical_project.md), system wymaga następujących głównych encji:
- Klient (użytkownik korzystający z usług)
- Wizyta (rezerwacja)
- Usługa (rodzaj świadczonych usług)
- Termin (dostępne sloty czasowe)
- Kody weryfikacyjne (aktywacja konta)

Musimy zaprojektować architekturę modeli Django, która:
- Będzie elastyczna i skalowalna
- Zapewni integralność danych
- Pozwoli na łatwe rozszerzanie funkcjonalności
- Będzie zgodna z best practices Django

## Decyzja

Implementujemy następującą architekturę modeli Django z podziałem na aplikacje:

### Aplikacja `accounts` (zarządzanie użytkownikami)

```python
# Model UserProfile (rozszerzenie Django User)
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    preferred_contact = models.CharField(choices=[('email', 'E-mail'), ('sms', 'SMS')])
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Aplikacja `bookings` (rezerwacje i usługi)

```python
# Model Service (rodzaje usług)
class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.DurationField()  # np. timedelta(minutes=30)
    color = models.CharField(max_length=7)  # hex color
    icon = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    
# Model TimeSlot (dostępne terminy)
class TimeSlot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    duration = models.DurationField()
    status = models.CharField(choices=[
        ('available', 'Dostępny'),
        ('booked', 'Zajęty'),
        ('blocked', 'Zablokowany')
    ])
    
# Model Booking (wizyty)
class Booking(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    time_slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    terms_accepted = models.BooleanField(default=False)
    status = models.CharField(choices=[
        ('scheduled', 'Zaplanowana'),
        ('cancelled', 'Odwołana'),
        ('completed', 'Zrealizowana')
    ])
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Aplikacja `verification` (weryfikacja)

```python
# Model ActivationCode
class ActivationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    channel = models.CharField(choices=[('sms', 'SMS'), ('email', 'E-mail')])
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Uzasadnienie

### Wykorzystanie Django User Model
- Używamy wbudowanego `django.contrib.auth.User` i rozszerzamy go przez `UserProfile`
- Separacja danych autentykacji od danych biznesowych
- Kompatybilność z Django admin i authentication system

### Relacje między modelami
- **OneToOneField**: `UserProfile.user`, `Booking.time_slot` - unikalna relacja
- **ForeignKey**: `Booking.client`, `TimeSlot.service` - relacja wiele-do-jednego
- **on_delete=CASCADE**: usunięcie nadrzędnego obiektu usuwa powiązane
- **on_delete=PROTECT**: zabezpieczenie przed usunięciem używanych usług

### Statusy jako choices
- Walidacja na poziomie bazy danych
- Łatwe zarządzanie stanami w Django admin
- Możliwość rozszerzenia o workflow states

### DurationField dla czasu trwania
- Elastyczność (różne usługi = różne czasy)
- Łatwe obliczanie końca wizyty
- Wsparcie dla Python timedelta

## Konsekwencje

### Pozytywne
- Czysta separacja odpowiedzialności (SoC)
- Łatwe rozszerzanie o nowe pola
- Wsparcie dla Django ORM queries
- Integralność referencyjna na poziomie bazy
- Gotowe do integracji z Django admin

### Negatywne
- Wymaga wielu join'ów dla złożonych zapytań
- Potencjalne problemy z wydajnością przy dużej liczbie rezerwacji (wymaga indeksów)
- Konieczność synchronizacji statusów między TimeSlot a Booking

### Migracje
- Wymaga stworzenia migracji początkowych dla wszystkich aplikacji
- Należy zastosować indeksy na: `start_datetime`, `status`, `phone_number`

## Implementacja

Struktura aplikacji:

```text
project/
├── accounts/
│   ├── models.py      # UserProfile
│   └── migrations/
├── bookings/
│   ├── models.py      # Service, TimeSlot, Booking
│   └── migrations/
└── verification/
    ├── models.py      # ActivationCode
    └── migrations/
```

### Indeksy bazodanowe

```python
class Booking:
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

class TimeSlot:
    class Meta:
        indexes = [
            models.Index(fields=['start_datetime', 'status']),
        ]
```

## Alternatywy rozważone

1. **Jeden duży model User** - Odrzucone (zbyt duży model, trudny w utrzymaniu)
2. **NoSQL (MongoDB)** - Odrzucone (relacyjność danych wymaga SQL)
3. **Termin jako część Booking** - Odrzucone (brak możliwości zarządzania slotami przed rezerwacją)

## Odniesienia

- Django Models: <https://docs.djangoproject.com/en/stable/topics/db/models/>
- Django Model Field Reference: <https://docs.djangoproject.com/en/stable/ref/models/fields/>
- Database Indexes: <https://docs.djangoproject.com/en/stable/ref/models/indexes/>
