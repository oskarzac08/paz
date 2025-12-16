from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import random
import string



def validate_file_size(value):
    limit = 20 * 1024 * 1024  # 20 MB
    if value.size > limit:
        raise ValidationError('Plik jest zbyt duży. Maksymalny rozmiar to 20 MB.')


# Create your models here.
class Idea(models.Model):
    title = models.CharField(max_length=200, verbose_name='Tytuł')
    description = models.TextField(verbose_name='Opis')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True, verbose_name='Autor')

    class Meta:
        verbose_name = 'Pomysł'
        verbose_name_plural = 'Pomysły'

    def __str__(self):
        return self.title


class IdeaImage(models.Model):
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name='images', verbose_name='Pomysł')
    image = models.ImageField(upload_to='idea_images/', null=True, blank=True, validators=[validate_file_size], verbose_name='Zdjęcie')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Data przesłania')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_images', verbose_name='Przesłane przez')

    class Meta:
        verbose_name = 'Zdjęcie pomysłu'
        verbose_name_plural = 'Zdjęcia pomysłów'

    def __str__(self):
        return f"{self.idea.title} - zdjęcie {self.id}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name='Użytkownik')
    phone_number = models.CharField(max_length=15, blank=True, verbose_name='Numer telefonu')
    preferred_contact = models.CharField(
        max_length=10,
        choices=[('email', 'E-mail'), ('sms', 'SMS'), ('both', 'Oba')],
        default='email',
        verbose_name='Preferowany kontakt'
    )
    email_verified = models.BooleanField(default=False, verbose_name='E-mail zweryfikowany')
    phone_verified = models.BooleanField(default=False, verbose_name='Telefon zweryfikowany')
    activation_date = models.DateTimeField(null=True, blank=True, verbose_name='Data aktywacji')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    
    # Historia wizyt i preferencje (PDR-008)
    SEGMENT_CHOICES = [
        ('new', 'Nowy (< 3 wizyty)'),
        ('regular', 'Regularny (3-9 wizyt)'),
        ('vip', 'VIP (10+ wizyt)'),
        ('at_risk', 'Zagrożony (brak wizyty > 90 dni)'),
        ('problematic', 'Problematyczny (>50% odwołań)'),
    ]
    
    customer_segment = models.CharField(
        max_length=20,
        choices=SEGMENT_CHOICES,
        default='new',
        verbose_name='Segment klienta',
        help_text='Automatycznie aktualizowany'
    )
    total_visits = models.PositiveIntegerField(
        default=0,
        verbose_name='Łączna liczba wizyt'
    )
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Łączne wydatki (PLN)'
    )
    last_visit_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data ostatniej wizyty'
    )
    favorite_service = models.ForeignKey(
        'Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='favorited_by',
        verbose_name='Ulubiona usługa'
    )
    
    # Notatki obsługi (staff only)
    staff_notes = models.TextField(
        blank=True,
        verbose_name='Notatki obsługi',
        help_text='Widoczne tylko dla obsługi - preferencje, uwagi, alergie'
    )

    class Meta:
        verbose_name = 'Profil użytkownika'
        verbose_name_plural = 'Profile użytkowników'

    def __str__(self):
        return f"Profil: {self.user.get_full_name() or self.user.username}"
    
    @property
    def is_verified(self):
        """Sprawdza czy użytkownik ma zweryfikowany przynajmniej jeden kanał"""
        return self.email_verified or self.phone_verified
    
    @property
    def segment_badge(self):
        """Zwraca emoji badge dla segmentu"""
        badges = {
            'new': '🌟',
            'regular': '👍',
            'vip': '🏆',
            'at_risk': '⚠️',
            'problematic': '🚫',
        }
        return badges.get(self.customer_segment, '')
    
    @property
    def average_visit_interval(self):
        """Oblicza średni interwał między wizytami w dniach"""
        from django.db.models import Avg
        from datetime import timedelta
        
        completed_reservations = self.user.reservations.filter(
            status='completed'
        ).order_by('start')
        
        if completed_reservations.count() < 2:
            return None
        
        # Oblicz różnice między kolejnymi wizytami
        intervals = []
        prev_visit = None
        for reservation in completed_reservations:
            if prev_visit:
                delta = (reservation.start - prev_visit).days
                intervals.append(delta)
            prev_visit = reservation.start
        
        if intervals:
            return sum(intervals) / len(intervals)
        return None
    
    def update_segment(self):
        """Automatycznie aktualizuje segment klienta na podstawie historii"""
        from datetime import timedelta
        
        # Pobierz statystyki
        total_reservations = self.user.reservations.count()
        completed = self.user.reservations.filter(status='completed').count()
        cancelled = self.user.reservations.filter(status='cancelled').count()
        no_show = self.user.reservations.filter(status='no_show').count()
        
        # Oblicz procent odwołań + no-show
        if total_reservations > 0:
            problem_rate = (cancelled + no_show) / total_reservations
        else:
            problem_rate = 0
        
        # Segmentacja
        if problem_rate > 0.5 and total_reservations >= 3:
            new_segment = 'problematic'
        elif completed >= 10:
            # Sprawdź czy at-risk (brak wizyty > 90 dni)
            if self.last_visit_date:
                days_since = (timezone.now() - self.last_visit_date).days
                if days_since > 90:
                    new_segment = 'at_risk'
                else:
                    new_segment = 'vip'
            else:
                new_segment = 'vip'
        elif completed >= 3:
            new_segment = 'regular'
        else:
            new_segment = 'new'
        
        if new_segment != self.customer_segment:
            self.customer_segment = new_segment
            self.save(update_fields=['customer_segment'])
    
    def update_stats(self):
        """Aktualizuje statystyki użytkownika"""
        from django.db.models import Sum, Max, Count
        
        # Liczba wizyt (completed)
        completed_count = self.user.reservations.filter(status='completed').count()
        self.total_visits = completed_count
        
        # Łączne wydatki
        total = self.user.reservations.filter(
            status='completed'
        ).aggregate(
            total=Sum('service__price')
        )['total'] or 0
        self.total_spent = total
        
        # Data ostatniej wizyty
        last_visit = self.user.reservations.filter(
            status='completed'
        ).aggregate(
            last=Max('start')
        )['last']
        self.last_visit_date = last_visit
        
        # Ulubiona usługa (najczęściej wybierana)
        favorite = self.user.reservations.filter(
            status='completed'
        ).values('service').annotate(
            count=Count('service')
        ).order_by('-count').first()
        
        if favorite:
            from .models import Service
            self.favorite_service_id = favorite['service']
        
        self.save()
        
        # Aktualizuj segment
        self.update_segment()


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class ActivationCode(models.Model):
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'E-mail'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activation_codes', verbose_name='Użytkownik')
    code = models.CharField(max_length=6, default='000000', verbose_name='Kod')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email', verbose_name='Kanał')
    expires_at = models.DateTimeField(verbose_name='Wygasa')
    is_used = models.BooleanField(default=False, verbose_name='Użyty')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Utworzony')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Użyty o')

    class Meta:
        verbose_name = 'Kod aktywacyjny'
        verbose_name_plural = 'Kody aktywacyjne'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'channel']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Kod dla {self.user.get_full_name() or self.user.username} przez {self.channel}"
    
    @property
    def is_expired(self):
        """Sprawdza czy kod wygasł"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Sprawdza czy kod jest ważny (nie użyty i nie wygasły)"""
        return not self.is_used and not self.is_expired

    def mark_used(self):
        """Oznacza kod jako użyty"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class ServiceCategory(models.Model):
    """Kategoria usług (opcjonalna, dla > 10 usług)"""
    name = models.CharField(max_length=100, verbose_name='Nazwa kategorii')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Opis')
    order = models.PositiveIntegerField(default=0, verbose_name='Kolejność')
    is_active = models.BooleanField(default=True, verbose_name='Aktywna')
    
    class Meta:
        verbose_name = 'Kategoria usług'
        verbose_name_plural = 'Kategorie usług'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Service(models.Model):
    """Usługa dostępna do rezerwacji"""
    # Podstawowe informacje
    name = models.CharField(max_length=200, verbose_name='Nazwa')
    description = models.TextField(blank=True, verbose_name='Opis')  # Zachowane dla kompatybilności
    description_short = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name='Krótki opis',
        help_text='2-3 zdania, widoczne na kafelku'
    )
    description_full = models.TextField(
        blank=True, 
        verbose_name='Pełny opis',
        help_text='Szczegółowy opis usługi, markdown support'
    )
    
    # Parametry usługi
    duration_minutes = models.PositiveIntegerField(default=30, verbose_name='Czas trwania (min)')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Cena')
    
    # Kategoria (opcjonalna)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name='Kategoria'
    )
    
    # Wizualizacja
    color = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name='Kolor',
        help_text='Kolor HEX dla kalendarza (np. #FF5733)'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Ikona',
        help_text='Nazwa ikony z FontAwesome/Material Icons (np. fa-cut, fa-palette)'
    )
    
    # Status i kolejność
    is_active = models.BooleanField(default=True, verbose_name='Aktywna')
    order = models.PositiveIntegerField(default=0, verbose_name='Kolejność')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')
    
    # Statystyki
    booking_count = models.PositiveIntegerField(default=0, verbose_name='Liczba rezerwacji')

    class Meta:
        verbose_name = 'Usługa'
        verbose_name_plural = 'Usługi'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'order']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return self.name
    
    @property
    def primary_image(self):
        """Zwraca główne zdjęcie usługi"""
        return self.images.filter(is_primary=True).first()
    
    @property
    def gallery_images(self):
        """Zwraca wszystkie zdjęcia w galerii (poza głównym)"""
        return self.images.filter(is_primary=False).order_by('order')
    
    @property
    def all_images(self):
        """Zwraca wszystkie zdjęcia"""
        return self.images.all().order_by('-is_primary', 'order')


class ServiceImage(models.Model):
    """Zdjęcia usług - galeria"""
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Usługa'
    )
    image = models.ImageField(
        upload_to='services/%Y/%m/',
        verbose_name='Zdjęcie',
        validators=[validate_file_size]
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Tekst alternatywny',
        help_text='Opis zdjęcia dla dostępności (alt)'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Główne zdjęcie',
        help_text='Główne zdjęcie wyświetlane na kafelku'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Kolejność',
        help_text='Kolejność w galerii'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_images',
        verbose_name='Dodane przez'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')
    
    class Meta:
        verbose_name = 'Zdjęcie usługi'
        verbose_name_plural = 'Zdjęcia usług'
        ordering = ['-is_primary', 'order', '-uploaded_at']
        indexes = [
            models.Index(fields=['service', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - zdjęcie {self.id} {'(główne)' if self.is_primary else ''}"
    
    def save(self, *args, **kwargs):
        # Tylko jedno główne zdjęcie per usługa
        if self.is_primary:
            ServiceImage.objects.filter(
                service=self.service,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class RecurringSlotTemplate(models.Model):
    """Szablon dla cyklicznych slotów czasowych"""
    name = models.CharField(max_length=200, verbose_name='Nazwa szablonu')
    description = models.TextField(blank=True, verbose_name='Opis')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='slot_templates', verbose_name='Usługa')
    
    # Konfiguracja dni tygodnia
    monday = models.BooleanField(default=True, verbose_name='Poniedziałek')
    tuesday = models.BooleanField(default=True, verbose_name='Wtorek')
    wednesday = models.BooleanField(default=True, verbose_name='Środa')
    thursday = models.BooleanField(default=True, verbose_name='Czwartek')
    friday = models.BooleanField(default=True, verbose_name='Piątek')
    saturday = models.BooleanField(default=False, verbose_name='Sobota')
    sunday = models.BooleanField(default=False, verbose_name='Niedziela')
    
    # Godziny pracy
    start_time = models.TimeField(default='09:00', verbose_name='Godzina rozpoczęcia')
    end_time = models.TimeField(default='17:00', verbose_name='Godzina zakończenia')
    slot_interval_minutes = models.PositiveIntegerField(default=30, verbose_name='Interwał slotów (min)')
    
    # Przerwy (JSON: [{"start": "13:00", "end": "14:00", "name": "Lunch"}])
    breaks = models.JSONField(default=list, blank=True, verbose_name='Przerwy')
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates',
        verbose_name='Utworzone przez'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')
    is_active = models.BooleanField(default=True, verbose_name='Aktywny')
    
    class Meta:
        verbose_name = 'Szablon cyklicznych slotów'
        verbose_name_plural = 'Szablony cyklicznych slotów'
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.service.name})"
    
    @property
    def active_days(self):
        """Zwraca listę aktywnych dni tygodnia"""
        days = []
        day_map = {
            0: ('monday', 'Pon'),
            1: ('tuesday', 'Wt'),
            2: ('wednesday', 'Śr'),
            3: ('thursday', 'Czw'),
            4: ('friday', 'Pt'),
            5: ('saturday', 'Sob'),
            6: ('sunday', 'Nie'),
        }
        for day_num, (field_name, label) in day_map.items():
            if getattr(self, field_name):
                days.append(label)
        return days


class TimeSlot(models.Model):
    """Slot czasowy dla rezerwacji"""
    STATUS_CHOICES = [
        ('available', 'Dostępny'),
        ('booked', 'Zajęty'),
        ('blocked', 'Zablokowany'),
    ]
    
    BLOCK_REASON_CHOICES = [
        ('vacation', 'Urlop'),
        ('break', 'Przerwa'),
        ('training', 'Szkolenie'),
        ('maintenance', 'Konserwacja'),
        ('other', 'Inny powód'),
    ]
    
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='timeslots',
        verbose_name='Usługa',
        null=True,
        blank=True,
        help_text='Pozostaw puste dla blokady dotyczącej wszystkich usług'
    )
    start = models.DateTimeField(verbose_name='Początek')
    end = models.DateTimeField(verbose_name='Koniec')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='Status'
    )
    
    # Blokada
    block_reason = models.CharField(
        max_length=20,
        choices=BLOCK_REASON_CHOICES,
        blank=True,
        verbose_name='Powód blokady'
    )
    block_note = models.TextField(
        blank=True,
        verbose_name='Notatka blokady',
        help_text='Widoczne tylko dla obsługi'
    )
    
    # Cykliczność
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='Cykliczny',
        help_text='Czy slot został utworzony przez szablon cykliczny'
    )
    recurring_group_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name='ID grupy cyklicznej',
        help_text='UUID identyfikujący grupę cyklicznie utworzonych slotów'
    )
    template = models.ForeignKey(
        RecurringSlotTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_slots',
        verbose_name='Szablon'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_timeslots',
        verbose_name='Utworzone przez'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'Slot czasowy'
        verbose_name_plural = 'Sloty czasowe'
        ordering = ['start']
        indexes = [
            models.Index(fields=['service', 'start', 'status']),
            models.Index(fields=['status', 'start']),
            models.Index(fields=['recurring_group_id']),
        ]

    def __str__(self):
        service_name = self.service.name if self.service else "Wszystkie usługi"
        if not self.start:
            return f"{service_name} (nowy slot)"
        return f"{service_name}: {self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%H:%M')} ({self.get_status_display()})"
    
    @property
    def duration_minutes(self):
        """Zwraca czas trwania w minutach"""
        if self.start and self.end:
            return int((self.end - self.start).total_seconds() / 60)
        return 0
    
    @property
    def is_available(self):
        """Sprawdza czy slot jest dostępny"""
        if not self.start:
            return False
        return self.status == 'available' and self.start > timezone.now()
    
    @property
    def is_past(self):
        """Sprawdza czy slot jest z przeszłości"""
        if not self.start:
            return False
        return self.start < timezone.now()
    
    def can_be_booked(self):
        """Sprawdza czy slot może być zarezerwowany"""
        if self.status != 'available':
            return False, f"Slot jest {self.get_status_display().lower()}"
        
        if self.is_past:
            return False, "Nie można rezerwować slotów z przeszłości"
        
        # Sprawdź czy nie ma już rezerwacji
        if hasattr(self, 'reservation_slot') and self.reservation_slot.exists():
            return False, "Slot jest już zarezerwowany"
        
        return True, ""
    
    def block(self, reason='other', note='', blocked_by=None):
        """Blokuje slot - sprawdza czy nie ma rezerwacji"""
        if self.status == 'booked':
            raise ValidationError("Nie można zablokować zajętego slotu")
        
        # Sprawdź czy nie ma aktywnych rezerwacji w tym czasie
        active_reservations = Reservation.objects.filter(
            service=self.service,
            start__lt=self.end,
            end__gt=self.start,
            status__in=['pending', 'confirmed']
        )
        
        if active_reservations.exists():
            raise ValidationError(
                f"Nie można zablokować - istnieją {active_reservations.count()} aktywne rezerwacje w tym czasie"
            )
        
        self.status = 'blocked'
        self.block_reason = reason
        self.block_note = note
        if blocked_by:
            self.created_by = blocked_by
        self.save()
    
    def unblock(self):
        """Odblokowuje slot"""
        if self.status != 'blocked':
            raise ValidationError("Slot nie jest zablokowany")
        
        self.status = 'available'
        self.block_reason = ''
        self.block_note = ''
        self.save()


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Oczekująca'),
        ('confirmed', 'Potwierdzona'),
        ('cancelled', 'Anulowana'),
        ('completed', 'Zrealizowana'),
        ('no_show', 'Nieobecność'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('change_plans', 'Zmiana planów'),
        ('illness', 'Choroba'),
        ('cannot_attend', 'Nie mogę się stawić'),
        ('staff_cancelled', 'Odwołane przez salon'),
        ('other', 'Inny powód'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reservations', verbose_name='Usługa')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reservations', verbose_name='Użytkownik')
    
    # TimeSlot integration (optional - for new booking flow)
    timeslot = models.ForeignKey(
        'TimeSlot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservation_slot',
        verbose_name='Slot czasowy',
        help_text='Powiązany slot czasowy (nowy system)'
    )
    
    # Customer details (for both guest and registered users)
    customer_first_name = models.CharField(max_length=100, blank=True, verbose_name='Imię klienta')
    customer_last_name = models.CharField(max_length=100, blank=True, verbose_name='Nazwisko klienta')
    customer_email = models.EmailField(verbose_name='E-mail klienta')
    customer_phone = models.CharField(max_length=15, blank=True, verbose_name='Telefon klienta')
    
    # Booking details
    start = models.DateTimeField(verbose_name='Początek')
    end = models.DateTimeField(verbose_name='Koniec')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    
    # Guest booking support
    is_guest = models.BooleanField(default=False, verbose_name='Rezerwacja gościa')
    confirmation_code = models.CharField(max_length=10, blank=True, db_index=True, verbose_name='Kod potwierdzenia')
    
    # Cancellation details
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Data odwołania')
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='cancelled_reservations',
        verbose_name='Odwołane przez'
    )
    cancelled_by_staff = models.BooleanField(default=False, verbose_name='Odwołane przez obsługę')
    cancellation_reason = models.CharField(
        max_length=50, 
        choices=CANCELLATION_REASON_CHOICES, 
        blank=True,
        verbose_name='Powód odwołania'
    )
    cancellation_note = models.TextField(blank=True, verbose_name='Notatka odwołania')
    cancellation_token = models.CharField(max_length=64, blank=True, db_index=True, unique=True, null=True, verbose_name='Token odwołania')
    cancellation_token_expires = models.DateTimeField(null=True, blank=True, verbose_name='Token wygasa')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')
    notes = models.TextField(blank=True, verbose_name='Notatki')

    class Meta:
        verbose_name = 'Rezerwacja'
        verbose_name_plural = 'Rezerwacje'
        ordering = ['-start']
        indexes = [
            models.Index(fields=['start']),
        ]

    def __str__(self):
        customer = f"{self.customer_first_name} {self.customer_last_name}" if self.customer_first_name else self.customer_email
        return f"{self.service.name} - {customer} @ {self.start.strftime('%Y-%m-%d %H:%M')} ({self.get_status_display()})"

    def overlaps(self, start_dt, end_dt):
        return not (self.end <= start_dt or self.start >= end_dt)
    
    def generate_cancellation_token(self):
        """Generuje unikalny token do odwołania wizyty"""
        import secrets
        from datetime import timedelta
        
        self.cancellation_token = secrets.token_urlsafe(32)
        self.cancellation_token_expires = timezone.now() + timedelta(days=7)
        self.save(update_fields=['cancellation_token', 'cancellation_token_expires'])
        return self.cancellation_token
    
    def can_cancel(self, by_staff=False):
        """Sprawdza czy wizyta może być odwołana"""
        from datetime import timedelta
        
        # Nie można odwołać już odwołanej lub zrealizowanej wizyty
        if self.status in ['cancelled', 'completed', 'no_show']:
            return False, "Ta wizyta została już odwołana lub zrealizowana"
        
        # Nie można odwołać wizyty w przeszłości
        if self.start < timezone.now():
            return False, "Nie można odwołać wizyty, która już się odbyła"
        
        # Obsługa może odwołać w każdym momencie
        if by_staff:
            return True, ""
        
        # Klient musi odwołać minimum 24h przed
        hours_until = (self.start - timezone.now()).total_seconds() / 3600
        if hours_until < 24:
            return False, f"Za późno na odwołanie. Musisz odwołać wizytę minimum 24 godziny przed terminem. Do wizyty pozostało: {int(hours_until)} godz."
        
        return True, ""
    
    def cancel(self, cancelled_by=None, by_staff=False, reason='', note=''):
        """Odwołuje wizytę"""
        can_cancel, message = self.can_cancel(by_staff=by_staff)
        
        if not can_cancel:
            raise ValidationError(message)
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancelled_by_staff = by_staff
        self.cancellation_reason = reason
        self.cancellation_note = note
        self.save()
        
        # Odblokuj TimeSlot jeśli istnieje
        if self.timeslot:
            try:
                self.timeslot.status = 'available'
                self.timeslot.save()
            except Exception:
                pass  # Kontynuuj nawet jeśli odblokowanie nie powiedzie się
        
        return True
    
    @property
    def hours_until_appointment(self):
        """Zwraca liczbę godzin do wizyty"""
        if self.start and self.start > timezone.now():
            return (self.start - timezone.now()).total_seconds() / 3600
        return 0
    
    @property
    def can_cancel_deadline(self):
        """Zwraca deadline do odwołania (24h przed)"""
        from datetime import timedelta
        if self.start:
            return self.start - timedelta(hours=24)
        return None


class ReservationNote(models.Model):
    """Notatka obsługi do rezerwacji - widoczna tylko dla staff"""
    reservation = models.ForeignKey(
        'Reservation',
        on_delete=models.CASCADE,
        related_name='staff_notes',
        verbose_name='Rezerwacja'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Autor'
    )
    note = models.TextField(verbose_name='Notatka')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')
    is_important = models.BooleanField(
        default=False,
        verbose_name='Ważna',
        help_text='Np. alergie, wymagania specjalne'
    )
    
    class Meta:
        verbose_name = 'Notatka obsługi'
        verbose_name_plural = 'Notatki obsługi'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notatka do {self.reservation} ({self.author})"


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
        ('delivered', 'Dostarczone'),
        ('failed', 'Nieudane'),
        ('cancelled', 'Anulowane'),
    ]
    
    TYPE_CHOICES = [
        ('verification_code', 'Kod weryfikacyjny'),
        ('booking_confirmation', 'Potwierdzenie rezerwacji'),
        ('booking_reminder_24h', 'Przypomnienie 24h'),
        ('booking_reminder_2h', 'Przypomnienie 2h'),
        ('booking_cancelled', 'Odwołanie wizyty'),
        ('booking_modified', 'Zmiana w wizycie'),
        ('staff_new_booking', 'Nowa rezerwacja (obsługa)'),
        ('staff_cancellation', 'Odwołanie przez klienta (obsługa)'),
        ('staff_daily_report', 'Raport dzienny'),
        ('staff_weekly_report', 'Raport tygodniowy'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Użytkownik'
    )
    notification_type = models.CharField(
        max_length=50, 
        choices=TYPE_CHOICES,
        verbose_name='Typ powiadomienia'
    )
    channel = models.CharField(
        max_length=10, 
        choices=CHANNEL_CHOICES,
        verbose_name='Kanał'
    )
    recipient = models.CharField(
        max_length=255,
        verbose_name='Odbiorca',
        help_text='Email lub numer telefonu'
    )
    subject = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name='Temat'
    )
    message = models.TextField(verbose_name='Wiadomość')
    html_message = models.TextField(
        blank=True,
        verbose_name='Wiadomość HTML',
        help_text='Opcjonalnie dla email'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='Status'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Komunikat błędu'
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Liczba ponowień'
    )
    
    # Metadata - powiązanie z obiektami
    related_object_type = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name='Typ powiązanego obiektu',
        help_text='np. Reservation, ActivationCode'
    )
    related_object_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='ID powiązanego obiektu'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data utworzenia'
    )
    sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Data wysłania'
    )
    delivered_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Data dostarczenia'
    )
    
    # Tracking
    opened_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Data otwarcia',
        help_text='Dla email - tracking piksela'
    )
    clicked_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Data kliknięcia',
        help_text='Dla email - tracking linków'
    )
    
    class Meta:
        verbose_name = 'Powiadomienie'
        verbose_name_plural = 'Powiadomienia'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} -> {self.recipient} ({self.get_status_display()})"
    
    def mark_sent(self):
        """Oznacza powiadomienie jako wysłane"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_delivered(self):
        """Oznacza powiadomienie jako dostarczone"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_failed(self, error_msg=''):
        """Oznacza powiadomienie jako nieudane"""
        self.status = 'failed'
        self.error_message = error_msg
        self.save(update_fields=['status', 'error_message'])
    
    @property
    def is_email(self):
        return self.channel == 'email'
    
    @property
    def is_sms(self):
        return self.channel == 'sms'


class NotificationPreference(models.Model):
    """Preferencje użytkownika dotyczące powiadomień"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Użytkownik'
    )
    
    # Kanał preferowany
    preferred_channel = models.CharField(
        max_length=10,
        choices=[('email', 'E-mail'), ('sms', 'SMS'), ('both', 'Oba')],
        default='email',
        verbose_name='Preferowany kanał'
    )
    
    # Typ powiadomień - Transakcyjne (nie można wyłączyć)
    enable_booking_confirmation = models.BooleanField(
        default=True,
        verbose_name='Potwierdzenie rezerwacji',
        help_text='Nie można wyłączyć - wymagane'
    )
    enable_booking_cancellation = models.BooleanField(
        default=True,
        verbose_name='Potwierdzenie odwołania',
        help_text='Nie można wyłączyć - wymagane'
    )
    
    # Przypomnienia (można wyłączyć)
    enable_reminder_24h = models.BooleanField(
        default=True,
        verbose_name='Przypomnienie 24h przed wizytą'
    )
    enable_reminder_2h = models.BooleanField(
        default=True,
        verbose_name='Przypomnienie 2h przed wizytą'
    )
    
    # Zmiany
    enable_booking_changes = models.BooleanField(
        default=True,
        verbose_name='Powiadomienia o zmianach w wizycie'
    )
    
    # Marketing (opt-in)
    enable_marketing = models.BooleanField(
        default=False,
        verbose_name='Oferty promocyjne i marketing'
    )
    enable_newsletter = models.BooleanField(
        default=False,
        verbose_name='Newsletter'
    )
    
    # Godziny ciszy (dla nieważnych powiadomień)
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Początek godzin ciszy',
        help_text='np. 22:00'
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Koniec godzin ciszy',
        help_text='np. 08:00'
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data utworzenia'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Data aktualizacji'
    )
    
    class Meta:
        verbose_name = 'Preferencje powiadomień'
        verbose_name_plural = 'Preferencje powiadomień'
    
    def __str__(self):
        return f"Preferencje: {self.user.get_full_name() or self.user.username}"
    
    def should_send_notification(self, notification_type):
        """
        Sprawdza czy wysłać powiadomienie danego typu
        
        Args:
            notification_type: Typ powiadomienia z Notification.TYPE_CHOICES
        
        Returns:
            bool: True jeśli wysłać, False jeśli nie
        """
        # Transakcyjne zawsze wysyłamy
        transactional = [
            'verification_code',
            'booking_confirmation', 
            'booking_cancelled',
        ]
        if notification_type in transactional:
            return True
        
        # Przypomnienia
        if notification_type == 'booking_reminder_24h':
            return self.enable_reminder_24h
        if notification_type == 'booking_reminder_2h':
            return self.enable_reminder_2h
        
        # Zmiany
        if notification_type == 'booking_modified':
            return self.enable_booking_changes
        
        # Marketing
        if notification_type in ['marketing', 'newsletter']:
            return self.enable_marketing or self.enable_newsletter
        
        # Domyślnie wysyłaj
        return True
    
    def is_in_quiet_hours(self):
        """Sprawdza czy jesteśmy w godzinach ciszy"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        
        # Jeśli godziny ciszy przechodzą przez północ
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= now <= self.quiet_hours_end


@receiver(post_save, sender=get_user_model())
def create_notification_preferences(sender, instance, created, **kwargs):
    """Automatycznie tworzy preferencje powiadomień dla nowego użytkownika"""
    if created:
        NotificationPreference.objects.get_or_create(user=instance)