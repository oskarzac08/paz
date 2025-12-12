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
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title


class IdeaImage(models.Model):
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='idea_images/', null=True, blank=True, validators=[validate_file_size])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_images')

    def __str__(self):
        return f"{self.idea.title} - image {self.id}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    preferred_contact = models.CharField(
        max_length=10,
        choices=[('email', 'E-mail'), ('sms', 'SMS'), ('both', 'Oba')],
        default='email'
    )
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    activation_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile for {self.user.username}"
    
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
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activation_codes')
    code = models.CharField(max_length=6, default='000000')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email')
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'channel']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Code for {self.user.username} via {self.channel}"
    
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