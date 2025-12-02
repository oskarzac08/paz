from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    activation_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)