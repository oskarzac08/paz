# ADR-005: Zarządzanie plikami i mediami

## Status

Zaakceptowany

## Kontekst

System wymaga obsługi plików multimedialnych związanych z usługami:

- Zdjęcia usług (opisy wizualne dla klientów)
- Ikony usług (identyfikacja wizualna w kalendarzu)
- Potencjalnie dokumenty (regulaminy, zgody)
- Zdjęcia profilowe użytkowników (przyszła funkcjonalność)

### Wymagania

- Upload i zarządzanie obrazami dla usług
- Walidacja rozmiaru i typu plików
- Bezpieczne przechowywanie
- Wydajne serwowanie plików
- Możliwość skalowania (przyszłe przeniesienie do cloud storage)

## Decyzja

Implementujemy hybrydowy system zarządzania plikami z możliwością migracji do cloud storage:

### 1. Model dla obrazów

```python
# bookings/models.py

from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_image_size(image):
    """Walidacja rozmiaru obrazu (max 5MB)"""
    limit_mb = 5
    if image.size > limit_mb * 1024 * 1024:
        raise ValidationError(f'Obraz jest zbyt duży. Max rozmiar: {limit_mb}MB')

class ServiceImage(models.Model):
    """Zdjęcia usług"""
    service = models.ForeignKey(
        'Service',
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='services/%Y/%m/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size
        ]
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-uploaded_at']
    
    def save(self, *args, **kwargs):
        # Tylko jeden primary image per service
        if self.is_primary:
            ServiceImage.objects.filter(
                service=self.service,
                is_primary=True
            ).update(is_primary=False)
        super().save(*args, **kwargs)

class Service(models.Model):
    # ... inne pola
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text='Nazwa ikony z icon library (np. FontAwesome)'
    )
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text='Kolor HEX dla kalendarza'
    )
    
    @property
    def primary_image(self):
        """Zwraca główne zdjęcie usługi"""
        return self.images.filter(is_primary=True).first()
```

### 2. Storage Backend Configuration

```python
# settings.py

# Development - Local storage
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Production - opcjonalnie S3/Azure/GCS
else:
    # Przykład dla AWS S3
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = 'eu-central-1'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
# Maksymalny rozmiar upload
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

### 3. Image Processing z Pillow

```python
# bookings/utils.py

from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

class ImageProcessor:
    
    @staticmethod
    def resize_image(image_file, max_width=1200, max_height=1200, quality=85):
        """
        Zmniejsza rozmiar obrazu zachowując proporcje
        """
        img = Image.open(image_file)
        
        # Konwersja RGBA -> RGB dla JPEG
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize zachowując aspect ratio
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save do BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return InMemoryUploadedFile(
            output,
            'ImageField',
            f"{image_file.name.split('.')[0]}.jpg",
            'image/jpeg',
            sys.getsizeof(output),
            None
        )
    
    @staticmethod
    def create_thumbnail(image_file, size=(300, 300)):
        """Tworzy miniaturkę obrazu"""
        img = Image.open(image_file)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=75)
        thumb_io.seek(0)
        
        return thumb_io
```

### 4. Forms z walidacją

```python
# bookings/forms.py

from django import forms

class ServiceImageForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            # Sprawdź typ MIME
            from mimetypes import guess_type
            mime_type, _ = guess_type(image.name)
            
            if mime_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise forms.ValidationError('Nieobsługiwany format obrazu')
            
            # Automatyczne resize
            return ImageProcessor.resize_image(image)
        
        return image

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'duration', 'icon', 'color', 'is_active']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
```

### 5. Views dla upload'u

```python
# bookings/views.py

from django.contrib.auth.mixins import PermissionRequiredMixin

class ServiceImageUploadView(PermissionRequiredMixin, CreateView):
    """Upload zdjęć usług - tylko dla obsługi"""
    model = ServiceImage
    form_class = ServiceImageForm
    permission_required = 'bookings.add_serviceimage'
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        form.instance.service_id = self.kwargs['service_id']
        
        messages.success(self.request, 'Zdjęcie zostało dodane')
        return super().form_valid(form)

class ServiceImageDeleteView(PermissionRequiredMixin, DeleteView):
    """Usuwanie zdjęć"""
    model = ServiceImage
    permission_required = 'bookings.delete_serviceimage'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Usuń plik z dysku/S3
        if self.object.image:
            self.object.image.delete(save=False)
        
        return super().delete(request, *args, **kwargs)
```

### 6. URL Configuration

```python
# project/urls.py

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... inne URL patterns
]

# Serwowanie mediów w development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## Uzasadnienie

### Dlaczego upload_to z datą?

- **Organizacja**: Łatwiejsze zarządzanie plikami
- **Performance**: Mniejsze katalogi = szybszy listing
- **Backup**: Łatwiejsze backup'y przyrostowe

### Dlaczego automatyczny resize?

- **Bandwidth**: Mniejsze pliki = szybsze ładowanie
- **Storage**: Oszczędność miejsca
- **UX**: Szybsze strony dla użytkowników

### Dlaczego oddzielny model ServiceImage?

- **Flexibility**: Wiele zdjęć na usługę
- **Metadata**: Dodatkowe informacje (alt_text, is_primary)
- **Management**: Łatwiejsze zarządzanie w admin

## Konsekwencje

### Pozytywne

- Walidacja plików na poziomie modelu i formularza
- Automatyczna optymalizacja obrazów
- Łatwa migracja do cloud storage
- Bezpieczne przechowywanie
- Segregacja plików po datach

### Negatywne

- Resize w request cycle może być wolny (lepiej w Celery)
- Lokalne storage nie skaluje się dobrze
- Brak CDN dla lokalnego storage
- Wymaga Pillow (dodatkowa zależność)

### Performance considerations

**Optimization strategies:**

1. **Async processing** (Celery):

```python
@shared_task
def process_uploaded_image(image_id):
    """Procesuj obraz asynchronicznie"""
    image = ServiceImage.objects.get(id=image_id)
    # Resize, optimize, generate thumbnails
```

2. **CDN Integration**:

```python
# settings.py
AWS_S3_CUSTOM_DOMAIN = f'{AWS_CLOUDFRONT_DOMAIN}'
```

3. **Image formats**:
   - WebP dla nowoczesnych przeglądarek (mniejszy rozmiar)
   - JPEG fallback dla starszych

## Implementacja

### Instalacja zależności

```bash
pip install Pillow
pip install django-storages[s3]  # dla AWS S3
```

### Migrations

```python
# Dodaj do requirements.txt
Pillow>=10.0.0
django-storages[s3]>=1.14
boto3>=1.28
```

### Security considerations

```python
# settings.py

# Whitelist dozwolonych rozszerzeń
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']

# Skanowanie antywirusowe (opcjonalne, dla produkcji)
# Integracja z ClamAV lub AWS S3 virus scanning
```

## Alternatywy rozważone

1. **Tylko URL do zewnętrznych obrazów** - Brak kontroli nad dostępnością
2. **Base64 w bazie danych** - Bardzo zła praktyka, brak cachowania
3. **Bezpośredni upload do S3 z frontendu** - Trudniejsze w zarządzaniu permissions
4. **ImageKit/Cloudinary** - Dodatkowy koszt, vendor lock-in

## Migracja do produkcji

### Krok 1: Setup S3 bucket

```bash
aws s3 mb s3://my-booking-system-media
aws s3api put-bucket-cors --bucket my-booking-system-media --cors-configuration file://cors.json
```

### Krok 2: Migracja istniejących plików

```python
# management/commands/migrate_to_s3.py
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Migruj wszystkie ServiceImage do S3
        for image in ServiceImage.objects.all():
            if image.image:
                # S3 storage handle this automatically
                image.save()
```

## Odniesienia

- Django File Uploads: <https://docs.djangoproject.com/en/stable/topics/http/file-uploads/>
- django-storages: <https://django-storages.readthedocs.io/>
- Pillow Documentation: <https://pillow.readthedocs.io/>
- AWS S3 Best Practices: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html>
