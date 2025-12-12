# ADR-004: Architektura systemu rezerwacji

## Status

Zaakceptowany

## Kontekst

System musi obsługiwać złożony proces rezerwacji wizyt z następującymi wymaganiami:

### Funkcjonalności dla klienta

- Przeglądanie dostępnych terminów dla wybranej usługi
- Filtrowanie terminów po dacie i godzinie
- Rezerwacja terminu z akceptacją regulaminu
- Podgląd nadchodzących wizyt
- Odwoływanie wizyt (z ograniczeniami czasowymi)

### Funkcjonalności dla obsługi

- Tworzenie terminów (pojedyncze i cykliczne)
- Zarządzanie statusem terminów (dostępny/zajęty/zablokowany)
- Rezerwowanie wizyt w imieniu klientów
- Edycja i anulowanie rezerwacji
- Blokowanie terminów (urlopy, niedostępność)

### Wyzwania techniczne

- Zapobieganie double-booking (dwie osoby rezerwują ten sam termin)
- Wydajne wyszukiwanie dostępnych terminów
- Zarządzanie statusami (termin vs wizyta)
- Automatyzacja tworzenia cyklicznych terminów

## Decyzja

Implementujemy system rezerwacji oparty na następujących założeniach:

### 1. Architektura dwumodelowa: TimeSlot + Booking

```python
# bookings/models.py

class TimeSlot(models.Model):
    """Reprezentuje dostępny slot czasowy"""
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    duration = models.DurationField()
    status = models.CharField(max_length=20, choices=[
        ('available', 'Dostępny'),
        ('booked', 'Zajęty'),
        ('blocked', 'Zablokowany'),
    ], default='available')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_slots'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'status']),
            models.Index(fields=['service', 'start_datetime']),
        ]
        unique_together = ['service', 'start_datetime']
    
    @property
    def end_datetime(self):
        return self.start_datetime + self.duration

class Booking(models.Model):
    """Reprezentuje rezerwację klienta"""
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    time_slot = models.OneToOneField(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='booking'
    )
    service = models.ForeignKey('Service', on_delete=models.PROTECT)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Zaplanowana'),
        ('cancelled', 'Odwołana'),
        ('completed', 'Zrealizowana'),
    ], default='scheduled')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cancelled_bookings'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bookings'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
```

### 2. Service Layer dla logiki biznesowej

```python
# bookings/services.py

from django.db import transaction
from django.utils import timezone
from datetime import timedelta

class BookingService:
    
    @staticmethod
    @transaction.atomic
    def create_booking(client, time_slot_id, terms_accepted=True):
        """Tworzy rezerwację z zabezpieczeniem przed double-booking"""
        
        # Pobierz i zablokuj slot (SELECT FOR UPDATE)
        time_slot = TimeSlot.objects.select_for_update().get(
            id=time_slot_id,
            status='available'
        )
        
        # Sprawdź czy termin jest w przyszłości
        if time_slot.start_datetime <= timezone.now():
            raise ValueError("Nie można rezerwować terminów z przeszłości")
        
        # Utwórz rezerwację
        booking = Booking.objects.create(
            client=client,
            time_slot=time_slot,
            service=time_slot.service,
            terms_accepted=terms_accepted,
            terms_accepted_at=timezone.now() if terms_accepted else None,
            status='scheduled'
        )
        
        # Zmień status slotu
        time_slot.status = 'booked'
        time_slot.save()
        
        return booking
    
    @staticmethod
    @transaction.atomic
    def cancel_booking(booking, cancelled_by, min_hours_before=24):
        """Anuluje rezerwację z sprawdzeniem czasu"""
        
        # Sprawdź czy można anulować
        hours_until = (booking.time_slot.start_datetime - timezone.now()).total_seconds() / 3600
        
        if hours_until < min_hours_before:
            raise ValueError(
                f"Rezerwacja może być anulowana minimum {min_hours_before}h przed terminem"
            )
        
        # Anuluj rezerwację
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.cancelled_by = cancelled_by
        booking.save()
        
        # Zwolnij slot
        booking.time_slot.status = 'available'
        booking.time_slot.save()
        
        return booking
    
    @staticmethod
    def get_available_slots(service_id, start_date=None, end_date=None):
        """Pobiera dostępne sloty dla usługi"""
        
        filters = {
            'service_id': service_id,
            'status': 'available',
            'start_datetime__gte': timezone.now()
        }
        
        if start_date:
            filters['start_datetime__gte'] = start_date
        if end_date:
            filters['start_datetime__lte'] = end_date
            
        return TimeSlot.objects.filter(**filters).select_related('service')


class TimeSlotService:
    
    @staticmethod
    def create_recurring_slots(service, start_date, end_date, time_slots, weekdays=None):
        """
        Tworzy cykliczne sloty czasowe
        
        Args:
            service: Obiekt Service
            start_date: Data rozpoczęcia (datetime.date)
            end_date: Data zakończenia (datetime.date)
            time_slots: Lista tupli (godzina, minuta, czas_trwania_min)
                       np. [(9, 0, 30), (9, 30, 30), (10, 0, 30)]
            weekdays: Lista dni tygodnia (0=pon, 6=niedz), None = wszystkie dni
        """
        from datetime import datetime, timedelta
        
        slots_to_create = []
        current_date = start_date
        
        while current_date <= end_date:
            # Sprawdź dzień tygodnia
            if weekdays is None or current_date.weekday() in weekdays:
                
                for hour, minute, duration_minutes in time_slots:
                    start_datetime = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    
                    slots_to_create.append(
                        TimeSlot(
                            service=service,
                            start_datetime=start_datetime,
                            duration=timedelta(minutes=duration_minutes),
                            status='available'
                        )
                    )
            
            current_date += timedelta(days=1)
        
        # Bulk create dla wydajności
        TimeSlot.objects.bulk_create(slots_to_create, ignore_conflicts=True)
        
        return len(slots_to_create)
```

### 3. Zabezpieczenie przed race conditions

```python
# Używamy select_for_update() w transakcjach
@transaction.atomic
def create_booking(client, time_slot_id):
    time_slot = TimeSlot.objects.select_for_update().get(
        id=time_slot_id,
        status='available'
    )
    # ... reszta logiki
```

### 4. API Views dla klientów i obsługi

```python
# bookings/views.py

class AvailableSlotsView(LoginRequiredMixin, ListView):
    """Widok dostępnych terminów dla klienta"""
    model = TimeSlot
    template_name = 'bookings/available_slots.html'
    
    def get_queryset(self):
        service_id = self.request.GET.get('service')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        return BookingService.get_available_slots(
            service_id=service_id,
            start_date=date_from,
            end_date=date_to
        )

class CreateBookingView(LoginRequiredMixin, CreateView):
    """Tworzenie rezerwacji przez klienta"""
    model = Booking
    fields = ['time_slot', 'terms_accepted']
    
    def form_valid(self, form):
        try:
            booking = BookingService.create_booking(
                client=self.request.user,
                time_slot_id=form.cleaned_data['time_slot'].id,
                terms_accepted=form.cleaned_data['terms_accepted']
            )
            messages.success(self.request, 'Rezerwacja została utworzona')
            return redirect('booking_detail', pk=booking.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

class CancelBookingView(LoginRequiredMixin, View):
    """Anulowanie rezerwacji"""
    
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, client=request.user)
        
        try:
            BookingService.cancel_booking(
                booking=booking,
                cancelled_by=request.user
            )
            messages.success(request, 'Rezerwacja została anulowana')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('my_bookings')
```

## Uzasadnienie

### Dlaczego rozdzielenie TimeSlot i Booking?

- **Flexibility**: Sloty mogą istnieć bez rezerwacji
- **Management**: Obsługa może zarządzać slotami niezależnie
- **History**: Historia terminów niezależna od rezerwacji
- **Blocking**: Możliwość blokowania terminów bez tworzenia fake bookings

### Dlaczego select_for_update()?

- **Race conditions**: Zapobiega double-booking
- **Consistency**: Gwarantuje spójność danych
- **Database locks**: Wykorzystuje mechanizmy bazy danych

### Dlaczego bulk_create dla recurring slots?

- **Performance**: Tworzenie 1000 slotów w jednym query vs 1000 queries
- **Efficiency**: Znacznie szybsze dla cyklicznych terminów

## Konsekwencje

### Pozytywne

- Brak możliwości double-booking dzięki transakcjom
- Wydajne tworzenie cyklicznych terminów
- Czysta separacja logiki biznesowej
- Łatwe testowanie service layer
- Elastyczne zarządzanie terminami

### Negatywne

- Database locks mogą wpłynąć na wydajność przy dużym ruchu
- Bulk create nie wywołuje signals (trzeba używać ostrożnie)
- Wymaga odpowiedniej konfiguracji bazy (isolation level)
- Potencjalne deadlocks przy złej implementacji

### Performance considerations

- Indeksy na `start_datetime` i `status` - krytyczne dla wydajności
- `select_related('service')` - redukuje N+1 queries
- Cache dla popularnych zapytań (dostępne sloty na dziś)
- Partycjonowanie tabeli TimeSlot po dacie (dla dużych systemów)

## Implementacja

### Settings dla rezerwacji

```python
# settings.py
BOOKING_MIN_CANCEL_HOURS = 24  # minimum 24h przed wizytą
BOOKING_MAX_ADVANCE_DAYS = 90  # max 90 dni do przodu
BOOKING_SLOT_DURATION_CHOICES = [15, 30, 45, 60]  # minuty
```

### Celery tasks

```python
# bookings/tasks.py
@shared_task
def auto_complete_past_bookings():
    """Automatycznie oznacza przeszłe rezerwacje jako completed"""
    past_bookings = Booking.objects.filter(
        status='scheduled',
        time_slot__start_datetime__lt=timezone.now()
    )
    past_bookings.update(status='completed')
```

## Alternatywy rozważone

1. **Pojedynczy model Booking bez TimeSlot** - Brak możliwości zarządzania pustymi slotami
2. **Optimistic locking** - Słabsze niż pessimistic locking dla double-booking
3. **Redis dla dostępności** - Dodatkowa złożoność, trudniejsze recovery
4. **Event sourcing** - Overkill dla obecnych wymagań

## Odniesienia

- Django Transactions: <https://docs.djangoproject.com/en/stable/topics/db/transactions/>
- Select for Update: <https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update>
- Bulk Create: <https://docs.djangoproject.com/en/stable/ref/models/querysets/#bulk-create>
