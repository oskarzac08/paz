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
from django.middleware.csrf import get_token
from .forms import PolishUserCreationForm, VerificationCodeForm, ResendCodeForm
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import ActivationCode
from .services import VerificationService
import logging

logger = logging.getLogger(__name__)
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .utils import generate_code, store_code, verify_code
from .mailing import send_verification_code
from .models import Service, Reservation
from .forms import ServiceSelectForm, DateTimeSelectForm, ReservationConfirmForm
from django.views.decorators.http import require_GET
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import datetime
import pytz


class IdeaListView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    model = Idea
    template_name = 'ideas/idea_list.html'
    context_object_name = 'ideas'
    paginate_by = 20


def landing(request):
    # simple landing page with two buttons: login and register
    return render(request, 'landing.html')


def home(request):
    """Root view: redirect to landing page."""
    return redirect('ideas:landing')


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

    # Ensure a fresh CSRF token cookie is present when rendering the form
    try:
        get_token(request)
    except Exception:
        logger.exception('Failed to ensure CSRF token on register view')

    return render(request, 'register.html', {'form': form})


def dev_csrf_view(request):
    """Development helper: return current CSRF token in plain text (DEBUG only)."""
    from django.conf import settings
    if not settings.DEBUG:
        return redirect('ideas:landing')

    token = get_token(request)
    from django.http import JsonResponse
    return JsonResponse({'csrftoken': token})


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


@require_POST
def request_email_code(request):
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'ok': False, 'error': 'Brak email'}, status=400)

    code = generate_code(6)
    store_code(email, code)
    try:
        send_verification_code(email, code)
    except Exception:
        logger.exception('Failed to send verification email')
        return JsonResponse({'ok': False, 'error': 'Błąd wysyłania'}, status=500)

    return JsonResponse({'ok': True})


@require_POST
def confirm_email_code(request):
    email = request.POST.get('email', '').strip()
    code = request.POST.get('code', '').strip()

    if verify_code(email, code):
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'Nieprawidłowy lub wygasły kod'}, status=400)


def _slot_available(service, start_dt, end_dt):
    # Simple availability check: no overlapping confirmed reservations
    conflicts = Reservation.objects.filter(service=service, status__in=['pending', 'confirmed']).filter(
        start__lt=end_dt, end__gt=start_dt
    )
    return not conflicts.exists()


def booking_step_service(request):
    """Krok 1: wybór usługi"""
    if request.method == 'POST':
        form = ServiceSelectForm(request.POST)
        if form.is_valid():
            service = form.cleaned_data['service']
            request.session['booking_service_id'] = service.id
            return redirect('ideas:booking_datetime')
    else:
        form = ServiceSelectForm()
    return render(request, 'ideas/booking_service.html', {'form': form})


def booking_step_datetime(request):
    """Krok 2: wybór daty i godziny"""
    service_id = request.session.get('booking_service_id')
    if not service_id:
        messages.error(request, 'Wybierz najpierw usługę')
        return redirect('ideas:booking_service')

    service = Service.objects.get(id=service_id)

    if request.method == 'POST':
        form = DateTimeSelectForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            # combine into timezone-aware datetime
            tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
            start_dt = datetime.datetime.combine(date, time)
            start_dt = tz.localize(start_dt)
            end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)

            if not _slot_available(service, start_dt, end_dt):
                messages.error(request, 'Termin już niedostępny. Wybierz inny termin.')
                return redirect('ideas:booking_datetime')

            request.session['booking_start'] = start_dt.isoformat()
            request.session['booking_end'] = end_dt.isoformat()
            return redirect('ideas:booking_summary')
    else:
        form = DateTimeSelectForm()

    return render(request, 'ideas/booking_datetime.html', {'form': form, 'service': service})


def booking_step_summary(request):
    """Krok 3: podsumowanie i akceptacja regulaminu"""
    service_id = request.session.get('booking_service_id')
    start_iso = request.session.get('booking_start')
    end_iso = request.session.get('booking_end')
    if not (service_id and start_iso and end_iso):
        messages.error(request, 'Brak danych rezerwacji. Rozpocznij proces od nowa.')
        return redirect('ideas:booking_service')

    service = Service.objects.get(id=service_id)
    tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
    start_dt = datetime.datetime.fromisoformat(start_iso)
    if start_dt.tzinfo is None:
        start_dt = tz.localize(start_dt)
    end_dt = datetime.datetime.fromisoformat(end_iso)
    if end_dt.tzinfo is None:
        end_dt = tz.localize(end_dt)

    if request.method == 'POST':
        form = ReservationConfirmForm(request.POST)
        if form.is_valid():
            # final availability check
            if not _slot_available(service, start_dt, end_dt):
                messages.error(request, 'Termin już niedostępny. Wybierz inny termin.')
                return redirect('ideas:booking_datetime')

            # create reservation
            reservation = Reservation.objects.create(
                service=service,
                user=request.user if request.user.is_authenticated else None,
                customer_name=(request.user.get_full_name() if request.user.is_authenticated else ''),
                customer_email=(request.user.email if request.user.is_authenticated else ''),
                start=start_dt,
                end=end_dt,
                status='confirmed'
            )

            # send confirmation email with .ics
            try:
                subject = f"Potwierdzenie rezerwacji: {service.name}"
                context = {'reservation': reservation}
                body = render_to_string('ideas/booking_email.txt', context)
                email = EmailMessage(subject, body, to=[reservation.customer_email] if reservation.customer_email else None)
                # create basic .ics
                ics = (
                    'BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\n'
                    f'SUMMARY:{service.name}\n'
                    f'DTSTART:{reservation.start.strftime("%Y%m%dT%H%M%S")}\n'
                    f'DTEND:{reservation.end.strftime("%Y%m%dT%H%M%S")}\n'
                    'END:VEVENT\nEND:VCALENDAR'
                )
                email.attach(f"reservation-{reservation.id}.ics", ics, 'text/calendar')
                if reservation.customer_email:
                    email.send(fail_silently=True)
            except Exception:
                logger.exception('Failed to send booking email')

            request.session['booking_reservation_id'] = reservation.id
            return redirect('ideas:booking_confirm')
    else:
        form = ReservationConfirmForm()

    return render(request, 'ideas/booking_summary.html', {
        'form': form,
        'service': service,
        'start': start_dt,
        'end': end_dt,
    })


def booking_step_confirm(request):
    """Krok 4: potwierdzenie"""
    res_id = request.session.get('booking_reservation_id')
    if not res_id:
        messages.error(request, 'Brak potwierdzenia rezerwacji.')
        return redirect('ideas:booking_service')

    reservation = Reservation.objects.filter(id=res_id).first()
    return render(request, 'ideas/booking_confirm.html', {'reservation': reservation})
