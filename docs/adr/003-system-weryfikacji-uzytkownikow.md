# ADR-003: System weryfikacji użytkowników

## Status

Zaakceptowany

## Kontekst

Zgodnie z wymaganiami funkcjonalnymi, system musi weryfikować tożsamość użytkowników poprzez:

- Weryfikację numeru telefonu przez SMS
- Weryfikację adresu e-mail przez link aktywacyjny
- Zarządzanie kodami aktywacyjnymi (generowanie, wygasanie, jednorazowe użycie)

System musi obsługiwać dwa scenariusze:

1. **Samoobsługa** - klient rejestruje się sam i otrzymuje kod
2. **Rejestracja przez obsługę** - obsługa tworzy konto i wysyła powiadomienie

## Decyzja

Implementujemy system dwukanałowej weryfikacji z następującymi komponentami:

### 1. Model ActivationCode

```python
class ActivationCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)  # 6-cyfrowy kod
    channel = models.CharField(max_length=10, choices=[
        ('sms', 'SMS'),
        ('email', 'E-mail')
    ])
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['code', 'channel']),
            models.Index(fields=['expires_at']),
        ]
```

### 2. Service Layer dla weryfikacji

```python
# verification/services.py
import secrets
from datetime import timedelta
from django.utils import timezone

class VerificationService:
    
    @staticmethod
    def generate_code(user, channel='email'):
        """Generuje 6-cyfrowy kod weryfikacyjny"""
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(hours=24)
        
        activation_code = ActivationCode.objects.create(
            user=user,
            code=code,
            channel=channel,
            expires_at=expires_at
        )
        
        return activation_code
    
    @staticmethod
    def verify_code(user, code, channel):
        """Weryfikuje kod aktywacyjny"""
        try:
            activation = ActivationCode.objects.get(
                user=user,
                code=code,
                channel=channel,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            activation.is_used = True
            activation.save()
            
            # Aktualizuj status weryfikacji w profilu
            if channel == 'email':
                user.profile.email_verified = True
            else:
                user.profile.phone_verified = True
            user.profile.save()
            
            return True
        except ActivationCode.DoesNotExist:
            return False
```

### 3. Integracja z zewnętrznymi serwisami

```python
# verification/backends.py

class EmailVerificationBackend:
    """Wysyłka e-mail przez Django mail"""
    
    @staticmethod
    def send_code(email, code):
        from django.core.mail import send_mail
        
        send_mail(
            subject='Kod weryfikacyjny',
            message=f'Twój kod weryfikacyjny: {code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

class SMSVerificationBackend:
    """Wysyłka SMS przez zewnętrzne API (np. Twilio, SMSApi)"""
    
    @staticmethod
    def send_code(phone_number, code):
        # Integracja z SMS API
        # np. Twilio, SMSApi.pl, itp.
        pass
```

### 4. Views dla weryfikacji

```python
# verification/views.py

class SendVerificationCodeView(LoginRequiredMixin, View):
    """Wysłanie kodu weryfikacyjnego"""
    
    def post(self, request):
        channel = request.POST.get('channel')  # 'email' lub 'sms'
        
        # Generuj kod
        activation_code = VerificationService.generate_code(
            user=request.user,
            channel=channel
        )
        
        # Wyślij kod
        if channel == 'email':
            EmailVerificationBackend.send_code(
                request.user.email,
                activation_code.code
            )
        else:
            SMSVerificationBackend.send_code(
                request.user.profile.phone_number,
                activation_code.code
            )
        
        return JsonResponse({'status': 'sent'})

class VerifyCodeView(LoginRequiredMixin, View):
    """Weryfikacja kodu"""
    
    def post(self, request):
        code = request.POST.get('code')
        channel = request.POST.get('channel')
        
        is_valid = VerificationService.verify_code(
            user=request.user,
            code=code,
            channel=channel
        )
        
        if is_valid:
            return JsonResponse({'status': 'verified'})
        else:
            return JsonResponse({'status': 'invalid'}, status=400)
```

## Uzasadnienie

### Dlaczego osobny model ActivationCode?

- **Audytowalność** - historia wszystkich wygenerowanych kodów
- **Bezpieczeństwo** - możliwość limitowania prób
- **Wygasanie** - automatyczne zarządzanie ważnością kodów
- **Multi-channel** - wsparcie dla różnych kanałów komunikacji

### Dlaczego Service Layer?

- **Testowanie** - łatwiejsze mockowanie w testach
- **Reużywalność** - kod używany w różnych widokach
- **Separacja logiki** - czysta architektura

### Dlaczego backends dla komunikacji?

- **Wymienność** - łatwa zmiana dostawcy SMS/Email
- **Konfiguracja** - różne backends dla dev/prod
- **Testowanie** - mock backends w testach

## Konsekwencje

### Pozytywne

- Bezpieczna weryfikacja dwukanałowa
- Kody jednorazowe z czasem wygaśnięcia
- Łatwa integracja z zewnętrznymi API
- Historia weryfikacji w bazie
- Możliwość rate limiting

### Negatywne

- Zależność od zewnętrznych serwisów (SMS API)
- Koszty wysyłki SMS
- Wymaga cyklicznego czyszczenia wygasłych kodów
- Potencjalne problemy z dostarczalnością (spam filters)

### Zagrożenia bezpieczeństwa

**Mitigacje:**

- Rate limiting na generowanie kodów (max 3 na godzinę)
- Throttling na endpoint weryfikacji (max 5 prób na 5 min)
- Logowanie nieudanych prób weryfikacji
- Kodowanie SMS/Email (nie wysyłać linku bezpośredniego w SMS)

## Implementacja

### Celery task dla czyszczenia wygasłych kodów

```python
# verification/tasks.py
from celery import shared_task
from django.utils import timezone

@shared_task
def cleanup_expired_codes():
    """Usuń wygasłe kody starsze niż 7 dni"""
    threshold = timezone.now() - timedelta(days=7)
    ActivationCode.objects.filter(
        expires_at__lt=threshold
    ).delete()
```

### Settings

```python
# settings.py
VERIFICATION_CODE_EXPIRY_HOURS = 24
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_MAX_ATTEMPTS = 5
VERIFICATION_RATE_LIMIT = 3  # max 3 kody na godzinę

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587

# SMS backend (przykład dla Twilio)
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = '+48123456789'
```

## Alternatywy rozważone

1. **Django-allauth** - Kompleksowe rozwiązanie, ale overkill dla naszych potrzeb
2. **Token w URL dla e-mail** - Mniej user-friendly niż kod
3. **Wysyłka kodu w plaintext** - Bezpieczniejsze jest hash, ale mniej praktyczne
4. **Captcha zamiast SMS** - Nie weryfikuje numeru telefonu

## Odniesienia

- Django Email: <https://docs.djangoproject.com/en/stable/topics/email/>
- Twilio API: <https://www.twilio.com/docs/sms>
- SMSApi.pl Documentation: <https://www.smsapi.pl/docs>
- Django Rate Limiting: <https://django-ratelimit.readthedocs.io/>
