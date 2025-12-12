from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.views.generic import ListView
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Idea, UserProfile
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PolishUserCreationForm, VerificationCodeForm, ResendCodeForm
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import ActivationCode
from .services import VerificationService
import logging

logger = logging.getLogger(__name__)


class IdeaListView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    model = Idea
    template_name = 'ideas/idea_list.html'
    context_object_name = 'ideas'
    paginate_by = 20


def landing(request):
    # simple landing page with two buttons: login and register
    return render(request, 'landing.html')


@ensure_csrf_cookie
def register_view(request):
    """Rejestracja nowego użytkownika z weryfikacją dwukanałową"""
    if request.method == 'POST':
        form = PolishUserCreationForm(request.POST)
        if form.is_valid():
            # Utwórz użytkownika (nieaktywnego)
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.is_active = False  # Aktywacja po weryfikacji
            user.save()
            
            # Pobierz lub utwórz profil użytkownika (sygnał post_save może już utworzyć profil)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = form.cleaned_data.get('phone_number', '')
            profile.preferred_contact = form.cleaned_data.get('preferred_contact', 'email')
            profile.save()
            
            # Wyślij kody weryfikacyjne według preferencji
            channels_to_send = []
            if profile.preferred_contact == 'email':
                channels_to_send = ['email']
            elif profile.preferred_contact == 'sms':
                channels_to_send = ['sms']
            else:  # both
                channels_to_send = ['email', 'sms']
            
            codes_sent = []
            for channel in channels_to_send:
                activation_code = VerificationService.create_verification_code(user, channel)
                if activation_code:
                    if VerificationService.send_verification_code(user, channel, activation_code.code):
                        codes_sent.append(channel)
                        logger.info(f"Sent {channel} verification code to user {user.id}")
            
            # Zapisz user_id w sesji do weryfikacji
            request.session['pending_verification_user_id'] = user.id
            request.session['verification_channels'] = codes_sent
            
            messages.success(
                request,
                f'Konto utworzone. Kod weryfikacyjny wysłano na: {", ".join(codes_sent)}.'
            )
            return redirect('ideas:verify_code')
    else:
        form = PolishUserCreationForm()
    
    return render(request, 'register.html', {'form': form})


def verify_code_view(request):
    """Widok weryfikacji kodu"""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        messages.error(request, 'Brak oczekującej weryfikacji.')
        return redirect('ideas:register')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, 'Nieprawidłowa sesja weryfikacji.')
        return redirect('ideas:register')
    
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            # Spróbuj zweryfikować kod dla każdego kanału
            verified = False
            for channel in ['email', 'sms']:
                success, message = VerificationService.verify_code(user, code, channel)
                if success:
                    verified = True
                    
                    # Aktywuj użytkownika po pierwszej pomyślnej weryfikacji
                    if not user.is_active:
                        user.is_active = True
                        user.save()
                        profile.activation_date = timezone.now()
                        profile.save()
                    
                    # Zaloguj użytkownika
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    # Wyczyść sesję
                    if 'pending_verification_user_id' in request.session:
                        del request.session['pending_verification_user_id']
                    if 'verification_channels' in request.session:
                        del request.session['verification_channels']
                    
                    messages.success(request, 'Weryfikacja zakończona pomyślnie! Witamy!')
                    return redirect('ideas:idea_list')
            
            if not verified:
                messages.error(request, 'Nieprawidłowy lub wygasły kod weryfikacyjny.')
    else:
        form = VerificationCodeForm()
    
    channels = request.session.get('verification_channels', [])
    return render(request, 'verify_code.html', {
        'form': form,
        'user': user,
        'channels': channels
    })


def resend_verification_code(request):
    """Ponowne wysłanie kodu weryfikacyjnego"""
    user_id = request.session.get('pending_verification_user_id')
    if not user_id:
        messages.error(request, 'Brak oczekującej weryfikacji.')
        return redirect('ideas:register')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, 'Nieprawidłowa sesja weryfikacji.')
        return redirect('ideas:register')
    
    if request.method == 'POST':
        form = ResendCodeForm(request.POST)
        if form.is_valid():
            channel = form.cleaned_data['channel']
            
            # Sprawdź czy można wysłać kod (rate limiting)
            if not VerificationService.can_send_code(user, channel):
                messages.error(
                    request,
                    'Przekroczono limit wysłanych kodów. Spróbuj ponownie za godzinę.'
                )
                return redirect('ideas:verify_code')
            
            # Utwórz i wyślij nowy kod
            activation_code = VerificationService.create_verification_code(user, channel)
            if activation_code:
                if VerificationService.send_verification_code(user, channel, activation_code.code):
                    messages.success(request, f'Nowy kod wysłano na {channel}.')
                else:
                    messages.error(request, 'Błąd podczas wysyłania kodu.')
            else:
                messages.error(request, 'Nie można wysłać kodu. Spróbuj później.')
            
            return redirect('ideas:verify_code')
    else:
        form = ResendCodeForm()
    
    return render(request, 'resend_code.html', {'form': form, 'user': user})


@login_required
def verification_status_view(request):
    """Widok statusu weryfikacji użytkownika"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    return render(request, 'verification_status.html', {'profile': profile})
