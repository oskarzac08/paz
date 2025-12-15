"""
Booking flow views for guest and registered users
5-step process: Service -> Terms -> Calendar -> Auth -> Confirmation
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
import datetime
import pytz
import random
import string

from .models import Service, Reservation
from .forms import (
    ServiceSelectForm, TermsAcceptanceForm, DateTimeSelectForm,
    GuestBookingForm, RegisterAndBookForm
)
from .services import VerificationService


def generate_confirmation_code():
    """Generate 8-character confirmation code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def check_slot_availability(service, start_dt, end_dt):
    """Check if time slot is available"""
    conflicts = Reservation.objects.filter(
        service=service,
        status__in=['pending', 'confirmed']
    ).filter(
        start__lt=end_dt,
        end__gt=start_dt
    )
    return not conflicts.exists()


def get_available_time_slots(request):
    """API endpoint to get available time slots for a given date and service"""
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')
    
    if not date_str or not service_id:
        return JsonResponse({'error': 'Missing date or service_id'}, status=400)
    
    try:
        service = Service.objects.get(id=service_id)
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Service.DoesNotExist, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    # Working hours: 9:00 - 18:00
    start_hour = 9
    end_hour = 18
    slot_interval = 30  # minutes
    
    tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
    slots = []
    
    # Generate time slots
    current_time = datetime.time(start_hour, 0)
    end_time = datetime.time(end_hour, 0)
    
    while current_time < end_time:
        # Check if this slot can accommodate the service duration
        start_dt = tz.localize(datetime.datetime.combine(date, current_time))
        end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)
        
        # Don't offer slots that would end after working hours
        if end_dt.time() <= end_time and start_dt > timezone.now():
            available = check_slot_availability(service, start_dt, end_dt)
            slots.append({
                'time': current_time.strftime('%H:%M'),
                'available': available
            })
        
        # Next slot
        temp_dt = datetime.datetime.combine(date, current_time)
        temp_dt += datetime.timedelta(minutes=slot_interval)
        current_time = temp_dt.time()
    
    return JsonResponse({'slots': slots})


# Step 1: Select Service
def booking_step1_service(request):
    """Krok 1: Wybór usługi"""
    if request.method == 'POST':
        form = ServiceSelectForm(request.POST)
        if form.is_valid():
            service = form.cleaned_data['service']
            request.session['booking_service_id'] = service.id
            return redirect('ideas:booking_step2_terms')
    else:
        form = ServiceSelectForm()
    
    services = Service.objects.all()
    return render(request, 'ideas/booking/step1_service.html', {
        'form': form,
        'services': services
    })


# Step 2: Accept Terms
def booking_step2_terms(request):
    """Krok 2: Akceptacja regulaminu"""
    service_id = request.session.get('booking_service_id')
    if not service_id:
        messages.error(request, 'Wybierz najpierw usługę')
        return redirect('ideas:booking_step1_service')
    
    service = Service.objects.get(id=service_id)
    
    if request.method == 'POST':
        form = TermsAcceptanceForm(request.POST)
        if form.is_valid():
            request.session['booking_terms_accepted'] = True
            return redirect('ideas:booking_step3_calendar')
    else:
        form = TermsAcceptanceForm()
    
    return render(request, 'ideas/booking/step2_terms.html', {
        'form': form,
        'service': service
    })


# Step 3: Select Date/Time
def booking_step3_calendar(request):
    """Krok 3: Wybór terminu"""
    service_id = request.session.get('booking_service_id')
    terms_accepted = request.session.get('booking_terms_accepted')
    
    if not service_id or not terms_accepted:
        messages.error(request, 'Uzupełnij poprzednie kroki')
        return redirect('ideas:booking_step1_service')
    
    service = Service.objects.get(id=service_id)
    
    if request.method == 'POST':
        form = DateTimeSelectForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            
            # Combine into timezone-aware datetime
            tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
            start_dt = datetime.datetime.combine(date, time)
            start_dt = tz.localize(start_dt)
            end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)
            
            # Check availability
            if not check_slot_availability(service, start_dt, end_dt):
                messages.error(request, 'Termin już niedostępny. Wybierz inny.')
                return redirect('ideas:booking_step3_calendar')
            
            # Check if date is in the past
            if start_dt < timezone.now():
                messages.error(request, 'Nie można rezerwować terminów w przeszłości.')
                return redirect('ideas:booking_step3_calendar')
            
            request.session['booking_start'] = start_dt.isoformat()
            request.session['booking_end'] = end_dt.isoformat()
            return redirect('ideas:booking_step4_auth')
    else:
        form = DateTimeSelectForm()
    
    return render(request, 'ideas/booking/step3_calendar.html', {
        'form': form,
        'service': service
    })


# Step 4: Guest or Register/Login
def booking_step4_auth(request):
    """Krok 4: Dane użytkownika (gość lub rejestracja/logowanie)"""
    service_id = request.session.get('booking_service_id')
    start_iso = request.session.get('booking_start')
    
    if not (service_id and start_iso):
        messages.error(request, 'Sesja wygasła. Rozpocznij od nowa.')
        return redirect('ideas:booking_step1_service')
    
    service = Service.objects.get(id=service_id)
    tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
    start_dt = datetime.datetime.fromisoformat(start_iso)
    if start_dt.tzinfo is None:
        start_dt = tz.localize(start_dt)
    
    # Already authenticated
    if request.user.is_authenticated:
        return redirect('ideas:booking_step5_confirm')
    
    guest_form = GuestBookingForm()
    register_form = RegisterAndBookForm()
    
    if request.method == 'POST':
        booking_type = request.POST.get('booking_type')
        
        if booking_type == 'guest':
            guest_form = GuestBookingForm(request.POST)
            if guest_form.is_valid():
                request.session['booking_guest_data'] = {
                    'first_name': guest_form.cleaned_data['first_name'],
                    'last_name': guest_form.cleaned_data['last_name'],
                    'email': guest_form.cleaned_data['email'],
                    'phone': guest_form.cleaned_data['phone'],
                    'notes': guest_form.cleaned_data.get('notes', ''),
                }
                request.session['booking_is_guest'] = True
                return redirect('ideas:booking_step5_confirm')
        
        elif booking_type == 'register':
            register_form = RegisterAndBookForm(request.POST)
            if register_form.is_valid():
                # Create user
                user = register_form.save(commit=False)
                user.email = register_form.cleaned_data['email']
                user.first_name = register_form.cleaned_data['first_name']
                user.last_name = register_form.cleaned_data['last_name']
                user.is_active = True  # Auto-activate for now
                user.save()
                
                # Update profile
                profile = user.profile
                profile.phone_number = register_form.cleaned_data.get('phone_number', '')
                profile.save()
                
                # Log in user
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Konto utworzone pomyślnie!')
                return redirect('ideas:booking_step5_confirm')
    
    return render(request, 'ideas/booking/step4_auth.html', {
        'service': service,
        'start': start_dt,
        'guest_form': guest_form,
        'register_form': register_form
    })


# Step 5: Confirmation
def booking_step5_confirm(request):
    """Krok 5: Potwierdzenie rezerwacji"""
    service_id = request.session.get('booking_service_id')
    start_iso = request.session.get('booking_start')
    end_iso = request.session.get('booking_end')
    
    if not (service_id and start_iso and end_iso):
        messages.error(request, 'Brak danych rezerwacji.')
        return redirect('ideas:booking_step1_service')
    
    service = Service.objects.get(id=service_id)
    tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
    start_dt = datetime.datetime.fromisoformat(start_iso)
    end_dt = datetime.datetime.fromisoformat(end_iso)
    
    if start_dt.tzinfo is None:
        start_dt = tz.localize(start_dt)
    if end_dt.tzinfo is None:
        end_dt = tz.localize(end_dt)
    
    # Final availability check
    if not check_slot_availability(service, start_dt, end_dt):
        messages.error(request, 'Termin już niedostępny. Wybierz inny.')
        return redirect('ideas:booking_step3_calendar')
    
    if request.method == 'POST':
        # Create reservation
        is_guest = request.session.get('booking_is_guest', False)
        
        if is_guest:
            guest_data = request.session.get('booking_guest_data', {})
            reservation = Reservation.objects.create(
                service=service,
                user=None,
                customer_first_name=guest_data.get('first_name', ''),
                customer_last_name=guest_data.get('last_name', ''),
                customer_email=guest_data.get('email', ''),
                customer_phone=guest_data.get('phone', ''),
                start=start_dt,
                end=end_dt,
                status='confirmed',
                is_guest=True,
                confirmation_code=generate_confirmation_code(),
                notes=guest_data.get('notes', '')
            )
        else:
            # Registered user
            # Safely get phone number from profile if it exists
            try:
                phone_number = request.user.profile.phone_number
            except:
                phone_number = ''
            
            reservation = Reservation.objects.create(
                service=service,
                user=request.user,
                customer_first_name=request.user.first_name,
                customer_last_name=request.user.last_name,
                customer_email=request.user.email,
                customer_phone=phone_number,
                start=start_dt,
                end=end_dt,
                status='confirmed',
                is_guest=False,
                confirmation_code=generate_confirmation_code()
            )
        
        # Send confirmation email
        try:
            subject = f"Potwierdzenie rezerwacji - {service.name}"
            context = {
                'reservation': reservation,
                'service': service,
                'customer_name': f"{reservation.customer_first_name} {reservation.customer_last_name}"
            }
            body = render_to_string('ideas/booking/email_confirmation.txt', context)
            email = EmailMessage(subject, body, to=[reservation.customer_email])

            # Attach .ics file
            ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Stylistka Paznokci//Booking//PL
BEGIN:VEVENT
UID:{reservation.confirmation_code}@stylistka.pl
DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{reservation.start.strftime('%Y%m%dT%H%M%S')}
DTEND:{reservation.end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{service.name}
DESCRIPTION:Rezerwacja: {service.name}
LOCATION:Salon Stylistki Paznokci
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
            email.attach(f"rezerwacja-{reservation.id}.ics", ics_content, 'text/calendar')
            email.send(fail_silently=True)
        except Exception as e:
            import logging
            logging.error(f"Failed to send booking email: {e}")
        
        # Clear session
        for key in ['booking_service_id', 'booking_terms_accepted', 'booking_start', 
                    'booking_end', 'booking_is_guest', 'booking_guest_data']:
            request.session.pop(key, None)
        
        # Redirect to success page
        return redirect('ideas:booking_success', reservation_id=reservation.id)
    
    # GET: Show summary
    is_guest = request.session.get('booking_is_guest', False)
    if is_guest:
        guest_data = request.session.get('booking_guest_data', {})
        customer_name = f"{guest_data.get('first_name', '')} {guest_data.get('last_name', '')}"
        customer_email = guest_data.get('email', '')
    else:
        customer_name = f"{request.user.first_name} {request.user.last_name}" if request.user.is_authenticated else ''
        customer_email = request.user.email if request.user.is_authenticated else ''
    
    return render(request, 'ideas/booking/step5_confirm.html', {
        'service': service,
        'start': start_dt,
        'end': end_dt,
        'customer_name': customer_name,
        'customer_email': customer_email,
        'is_guest': is_guest
    })


# Success page
def booking_success(request, reservation_id):
    """Strona sukcesu po rezerwacji"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        messages.error(request, 'Rezerwacja nie znaleziona.')
        return redirect('ideas:home')
    
    # Generuj token odwołania jeśli jeszcze nie ma
    if not reservation.cancellation_token:
        reservation.generate_cancellation_token()
    
    return render(request, 'ideas/booking/success.html', {
        'reservation': reservation
    })
