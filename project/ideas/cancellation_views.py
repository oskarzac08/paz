"""
Cancellation views for appointments
Handles customer and staff cancellation flows
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseForbidden
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import Reservation, Service
from .forms import CancellationForm


@login_required
def my_reservations(request):
    """Lista wizyt zalogowanego użytkownika"""
    now = timezone.now()
    
    # Nadchodzące wizyty
    upcoming = Reservation.objects.filter(
        user=request.user,
        start__gte=now,
        status__in=['pending', 'confirmed']
    ).order_by('start').select_related('service')
    
    # Historia wizyt
    past = Reservation.objects.filter(
        user=request.user
    ).filter(
        models.Q(start__lt=now) | 
        models.Q(status__in=['cancelled', 'completed', 'no_show'])
    ).order_by('-start').select_related('service')[:10]
    
    # Statystyki
    total_count = Reservation.objects.filter(user=request.user).count()
    cancelled_count = Reservation.objects.filter(
        user=request.user, 
        status='cancelled',
        cancelled_by_staff=False
    ).count()
    no_show_count = Reservation.objects.filter(
        user=request.user, 
        status='no_show'
    ).count()
    completed_count = Reservation.objects.filter(
        user=request.user, 
        status='completed'
    ).count()
    
    cancellation_rate = (cancelled_count / total_count * 100) if total_count > 0 else 0
    no_show_rate = (no_show_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'upcoming_reservations': upcoming,
        'past_reservations': past,
        'stats': {
            'total': total_count,
            'cancelled': cancelled_count,
            'no_show': no_show_count,
            'completed': completed_count,
            'cancellation_rate': cancellation_rate,
            'no_show_rate': no_show_rate,
        }
    }
    
    return render(request, 'ideas/my_reservations.html', context)


@login_required
def cancel_reservation(request, reservation_id):
    """Odwołanie wizyty przez zalogowanego użytkownika"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Sprawdź czy użytkownik jest właścicielem rezerwacji
    if reservation.user != request.user:
        return HttpResponseForbidden("Nie masz uprawnień do odwołania tej wizyty.")
    
    # Sprawdź czy można odwołać
    can_cancel, error_message = reservation.can_cancel(by_staff=False)
    
    if request.method == 'POST':
        if not can_cancel:
            messages.error(request, error_message)
            return redirect('ideas:my_reservations')
        
        form = CancellationForm(request.POST)
        if form.is_valid():
            try:
                # Odwołaj wizytę
                reservation.cancel(
                    cancelled_by=request.user,
                    by_staff=False,
                    reason=form.cleaned_data['reason'],
                    note=form.cleaned_data.get('note', '')
                )
                
                # Wyślij powiadomienia
                send_cancellation_notifications(reservation)
                
                messages.success(
                    request, 
                    f'Wizyta została odwołana. Wysłaliśmy potwierdzenie na {reservation.customer_email}'
                )
                
                # Przekieruj do strony z sugestiami rebooking
                return redirect('ideas:cancellation_success', reservation_id=reservation.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('ideas:my_reservations')
    else:
        initial_data = {}
        form = CancellationForm(initial=initial_data)
    
    context = {
        'reservation': reservation,
        'can_cancel': can_cancel,
        'error_message': error_message,
        'form': form,
        'hours_until': reservation.hours_until_appointment,
        'deadline': reservation.can_cancel_deadline,
    }
    
    return render(request, 'ideas/cancel_reservation.html', context)


def cancel_with_token(request, token):
    """One-click cancellation z emaila (bez logowania)"""
    try:
        reservation = Reservation.objects.get(cancellation_token=token)
    except Reservation.DoesNotExist:
        messages.error(request, 'Nieprawidłowy lub wygasły link odwołania.')
        return redirect('ideas:idea_list')
    
    # Sprawdź czy token wygasł
    if reservation.cancellation_token_expires and reservation.cancellation_token_expires < timezone.now():
        messages.error(request, 'Link do odwołania wygasł. Zaloguj się aby odwołać wizytę.')
        return redirect('login')
    
    # Sprawdź czy można odwołać
    can_cancel, error_message = reservation.can_cancel(by_staff=False)
    
    if request.method == 'POST':
        if not can_cancel:
            messages.error(request, error_message)
            return render(request, 'ideas/cancellation_error.html', {
                'reservation': reservation,
                'error_message': error_message
            })
        
        form = CancellationForm(request.POST)
        if form.is_valid():
            try:
                # Odwołaj wizytę
                reservation.cancel(
                    cancelled_by=reservation.user,
                    by_staff=False,
                    reason=form.cleaned_data['reason'],
                    note=form.cleaned_data.get('note', '')
                )
                
                # Unieważnij token (jednorazowy)
                reservation.cancellation_token = None
                reservation.cancellation_token_expires = None
                reservation.save(update_fields=['cancellation_token', 'cancellation_token_expires'])
                
                # Wyślij powiadomienia
                send_cancellation_notifications(reservation)
                
                messages.success(
                    request, 
                    f'Wizyta została odwołana. Wysłaliśmy potwierdzenie na {reservation.customer_email}'
                )
                
                return redirect('ideas:cancellation_success', reservation_id=reservation.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'ideas/cancellation_error.html', {
                    'reservation': reservation,
                    'error_message': str(e)
                })
    else:
        form = CancellationForm()
    
    context = {
        'reservation': reservation,
        'can_cancel': can_cancel,
        'error_message': error_message,
        'form': form,
        'hours_until': reservation.hours_until_appointment,
        'deadline': reservation.can_cancel_deadline,
        'token_mode': True,
    }
    
    return render(request, 'ideas/cancel_reservation.html', context)


def cancellation_success(request, reservation_id):
    """Strona sukcesu po odwołaniu z sugestiami rebooking"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Sprawdź czy wizyta faktycznie została odwołana
    if reservation.status != 'cancelled':
        return redirect('ideas:my_reservations')
    
    # Znajdź dostępne terminy dla tej samej usługi
    now = timezone.now()
    service = reservation.service
    
    # Najbliższe 3 dni robocze
    suggested_slots = []
    date = now.date()
    days_checked = 0
    max_days = 14  # Sprawdź do 2 tygodni
    
    while len(suggested_slots) < 5 and days_checked < max_days:
        date += timedelta(days=1)
        days_checked += 1
        
        # Pomiń weekendy (opcjonalnie)
        if date.weekday() >= 5:  # 5=sobota, 6=niedziela
            continue
        
        # Sprawdź sloty dla tego dnia
        for hour in [9, 10, 11, 14, 15, 16, 17]:
            start_time = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.min.time().replace(hour=hour))
            )
            end_time = start_time + timedelta(minutes=service.duration_minutes)
            
            # Sprawdź dostępność
            from .booking_views import check_slot_availability
            if check_slot_availability(service, start_time, end_time):
                suggested_slots.append({
                    'date': date,
                    'time': start_time.time(),
                    'datetime': start_time,
                })
                
                if len(suggested_slots) >= 5:
                    break
    
    context = {
        'reservation': reservation,
        'service': service,
        'suggested_slots': suggested_slots,
    }
    
    return render(request, 'ideas/cancellation_success.html', context)


def send_cancellation_notifications(reservation):
    """Wysyła powiadomienia o odwołaniu wizyty"""
    
    # Użyj NotificationService dla zalogowanych użytkowników
    if reservation.user:
        try:
            from .notification_service import NotificationService
            NotificationService.send_cancellation_notification(
                reservation, 
                cancelled_by=reservation.cancelled_by
            )
            return  # NotificationService obsługuje też powiadomienia do obsługi
        except Exception as e:
            import logging
            logging.error(f"Failed to send notification via NotificationService: {e}")
            # Fallback do starego systemu poniżej
    
    # Fallback/legacy dla gości lub gdy NotificationService nie działa
    # E-mail do klienta
    customer_subject = f'Potwierdzenie odwołania wizyty - {reservation.service.name}'
    customer_context = {
        'reservation': reservation,
        'cancelled_by_customer': not reservation.cancelled_by_staff,
    }
    customer_message = render_to_string('ideas/emails/cancellation_customer.txt', customer_context)
    
    send_mail(
        customer_subject,
        customer_message,
        settings.DEFAULT_FROM_EMAIL,
        [reservation.customer_email],
        fail_silently=True,
    )
    
    # E-mail do obsługi (jeśli odwołane przez klienta)
    if not reservation.cancelled_by_staff:
        staff_subject = f'Klient odwołał wizytę - {reservation.start.strftime("%d.%m.%Y %H:%M")}'
        staff_context = {
            'reservation': reservation,
        }
        staff_message = render_to_string('ideas/emails/cancellation_staff.txt', staff_context)
        
        # Wysyłka do wszystkich staff/superuser
        from django.contrib.auth.models import User
        staff_emails = User.objects.filter(
            models.Q(is_staff=True) | models.Q(is_superuser=True)
        ).values_list('email', flat=True)
        
        if staff_emails:
            send_mail(
                staff_subject,
                staff_message,
                settings.DEFAULT_FROM_EMAIL,
                list(staff_emails),
                fail_silently=True,
            )


# Import needed for Q objects
from django.db import models
