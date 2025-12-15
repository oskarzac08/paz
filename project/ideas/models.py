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

    class Meta:
        verbose_name = 'Profil użytkownika'
        verbose_name_plural = 'Profile użytkowników'

    def __str__(self):
        return f"Profil: {self.user.get_full_name() or self.user.username}"
    
    @property
    def is_verified(self):
        """Sprawdza czy użytkownik ma zweryfikowany przynajmniej jeden kanał"""
        return self.email_verified or self.phone_verified


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


class Service(models.Model):
    """Usługa dostępna do rezerwacji"""
    name = models.CharField(max_length=200, verbose_name='Nazwa')
    description = models.TextField(blank=True, verbose_name='Opis')
    duration_minutes = models.PositiveIntegerField(default=30, verbose_name='Czas trwania (min)')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Cena')

    class Meta:
        verbose_name = 'Usługa'
        verbose_name_plural = 'Usługi'

    def __str__(self):
        return self.name


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Oczekująca'),
        ('confirmed', 'Potwierdzona'),
        ('cancelled', 'Anulowana'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reservations', verbose_name='Usługa')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reservations', verbose_name='Użytkownik')
    
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


class TimeSlot(models.Model):
    """Opcjonalne prekalkulowane dostępne sloty czasowe."""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='timeslots', verbose_name='Usługa')
    start = models.DateTimeField(verbose_name='Początek')
    end = models.DateTimeField(verbose_name='Koniec')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')

    class Meta:
        verbose_name = 'Slot czasowy'
        verbose_name_plural = 'Sloty czasowe'

    def __str__(self):
        return f"{self.service.name}: {self.start.strftime('%Y-%m-%d %H:%M')} - {self.end.strftime('%H:%M')}"