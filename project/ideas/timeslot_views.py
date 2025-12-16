"""
Staff views for TimeSlot management
Handles calendar view, slot creation, blocking, and bulk operations
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta, time
from calendar import monthrange
import json

from .models import TimeSlot, Service, RecurringSlotTemplate, Reservation
from .forms import (
    SingleTimeSlotForm,
    RecurringTimeSlotForm,
    CopyTimeSlotsForm,
    BlockTimeSlotsForm
)
from .timeslot_service import TimeSlotService


def is_staff_user(user):
    """Sprawdza czy użytkownik jest członkiem obsługi"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_user)
def staff_calendar_view(request):
    """Widok kalendarza dla obsługi"""
    # Pobierz parametry z URL
    view_type = request.GET.get('view', 'week')  # week, month, day
    date_str = request.GET.get('date')
    service_id = request.GET.get('service')
    
    # Parsuj datę lub użyj dzisiejszej
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.now().date()
    else:
        current_date = timezone.now().date()
    
    # Oblicz zakres dat
    if view_type == 'day':
        start_date = current_date
        end_date = current_date
    elif view_type == 'month':
        start_date = current_date.replace(day=1)
        last_day = monthrange(current_date.year, current_date.month)[1]
        end_date = current_date.replace(day=last_day)
    else:  # week
        # Znajdź poniedziałek
        days_since_monday = current_date.weekday()
        start_date = current_date - timedelta(days=days_since_monday)
        end_date = start_date + timedelta(days=6)
    
    # Pobierz sloty
    slots_query = TimeSlot.objects.filter(
        start__date__gte=start_date,
        start__date__lte=end_date
    ).select_related('service', 'created_by').prefetch_related(
        Prefetch('reservation_slot', queryset=Reservation.objects.select_related('customer'))
    ).order_by('start')
    
    if service_id:
        slots_query = slots_query.filter(service_id=service_id)
    
    slots = list(slots_query)
    
    # Pogrupuj sloty po dniach
    slots_by_day = {}
    current = start_date
    while current <= end_date:
        slots_by_day[current] = []
        current += timedelta(days=1)
    
    for slot in slots:
        slot_date = slot.start.date()
        if slot_date in slots_by_day:
            slots_by_day[slot_date].append(slot)
    
    # Pobierz usługi do filtra
    services = Service.objects.filter(is_active=True).order_by('name')
    
    # Oblicz nawigację
    if view_type == 'day':
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
    elif view_type == 'month':
        prev_month = current_date.replace(day=1) - timedelta(days=1)
        prev_date = prev_month.replace(day=1)
        last_day = monthrange(current_date.year, current_date.month)[1]
        next_date = current_date.replace(day=last_day) + timedelta(days=1)
    else:  # week
        prev_date = start_date - timedelta(days=7)
        next_date = end_date + timedelta(days=1)
    
    context = {
        'view_type': view_type,
        'current_date': current_date,
        'start_date': start_date,
        'end_date': end_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'slots_by_day': slots_by_day,
        'services': services,
        'selected_service': service_id,
        'total_slots': len(slots),
        'available_count': sum(1 for s in slots if s.status == 'available'),
        'booked_count': sum(1 for s in slots if s.status == 'booked'),
        'blocked_count': sum(1 for s in slots if s.status == 'blocked'),
    }
    
    return render(request, 'ideas/staff/calendar.html', context)


@login_required
@user_passes_test(is_staff_user)
def create_single_slot_view(request):
    """Widok tworzenia pojedynczego slotu"""
    if request.method == 'POST':
        form = SingleTimeSlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.start = form.cleaned_data['start']
            slot.end = form.cleaned_data['end']
            slot.created_by = request.user
            slot.save()
            
            messages.success(request, f'Slot utworzony: {slot.start.strftime("%Y-%m-%d %H:%M")}')
            return redirect('staff_calendar')
    else:
        form = SingleTimeSlotForm()
    
    context = {
        'form': form,
        'title': 'Utwórz pojedynczy slot'
    }
    
    return render(request, 'ideas/staff/slot_form.html', context)


@login_required
@user_passes_test(is_staff_user)
def create_recurring_slots_view(request):
    """Widok tworzenia cyklicznych slotów"""
    if request.method == 'POST':
        form = RecurringTimeSlotForm(request.POST)
        if form.is_valid():
            # Przygotuj dane
            service = form.cleaned_data['service']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            slot_interval = form.cleaned_data.get('slot_interval_minutes')
            breaks = form.cleaned_data.get('breaks_parsed', [])
            
            # Mapuj dni tygodnia
            days_of_week = []
            day_mapping = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
            }
            for day_name, day_num in day_mapping.items():
                if form.cleaned_data.get(day_name):
                    days_of_week.append(day_num)
            
            # Zapisz szablon jeśli wybrano
            template = None
            if form.cleaned_data.get('save_as_template'):
                template = RecurringSlotTemplate.objects.create(
                    name=form.cleaned_data['template_name'],
                    service=service,
                    monday=form.cleaned_data.get('monday', False),
                    tuesday=form.cleaned_data.get('tuesday', False),
                    wednesday=form.cleaned_data.get('wednesday', False),
                    thursday=form.cleaned_data.get('thursday', False),
                    friday=form.cleaned_data.get('friday', False),
                    saturday=form.cleaned_data.get('saturday', False),
                    sunday=form.cleaned_data.get('sunday', False),
                    start_time=start_time,
                    end_time=end_time,
                    slot_interval_minutes=slot_interval or service.duration_minutes,
                    breaks=breaks,
                    created_by=request.user,
                    is_active=True
                )
            
            # Utwórz sloty
            try:
                result = TimeSlotService.create_recurring_slots(
                    service=service,
                    start_date=start_date,
                    end_date=end_date,
                    days_of_week=days_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    slot_interval_minutes=slot_interval,
                    breaks=breaks,
                    created_by=request.user,
                    template=template
                )
                
                messages.success(
                    request,
                    f'Utworzono {result["created_count"]} slotów. '
                    f'Pominięto {result["skipped_count"]} konfliktujących.'
                )
                
                if template:
                    messages.info(request, f'Szablon "{template.name}" został zapisany.')
                
                return redirect('staff_calendar')
                
            except Exception as e:
                messages.error(request, f'Błąd podczas tworzenia slotów: {str(e)}')
    else:
        form = RecurringTimeSlotForm()
    
    # Pobierz istniejące szablony
    templates = RecurringSlotTemplate.objects.filter(
        is_active=True
    ).select_related('service').order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'title': 'Utwórz cykliczne sloty',
        'templates': templates
    }
    
    return render(request, 'ideas/staff/recurring_form.html', context)


@login_required
@user_passes_test(is_staff_user)
def apply_template_view(request, template_id):
    """Aplikuj szablon cyklicznych slotów"""
    template = get_object_or_404(RecurringSlotTemplate, pk=template_id, is_active=True)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if end_date < start_date:
                messages.error(request, 'Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.')
                return redirect('create_recurring_slots')
            
            result = TimeSlotService.apply_template(
                template=template,
                start_date=start_date,
                end_date=end_date,
                created_by=request.user
            )
            
            messages.success(
                request,
                f'Szablon "{template.name}" zastosowany. '
                f'Utworzono {result["created_count"]} slotów, pominięto {result["skipped_count"]}.'
            )
            
            return redirect('staff_calendar')
            
        except ValueError:
            messages.error(request, 'Nieprawidłowy format daty.')
            return redirect('create_recurring_slots')
    
    context = {
        'template': template
    }
    
    return render(request, 'ideas/staff/apply_template.html', context)


@login_required
@user_passes_test(is_staff_user)
def copy_slots_view(request):
    """Widok kopiowania slotów"""
    if request.method == 'POST':
        form = CopyTimeSlotsForm(request.POST)
        if form.is_valid():
            try:
                result = TimeSlotService.copy_slots(
                    source_start_date=form.cleaned_data['source_start_date'],
                    source_end_date=form.cleaned_data['source_end_date'],
                    target_start_date=form.cleaned_data['target_start_date'],
                    copy_blocked=form.cleaned_data.get('copy_blocked', False),
                    skip_existing=form.cleaned_data.get('skip_existing', True)
                )
                
                messages.success(
                    request,
                    f'Skopiowano {result["created_count"]} slotów. '
                    f'Pominięto {result["skipped_count"]} istniejących.'
                )
                
                return redirect('staff_calendar')
                
            except Exception as e:
                messages.error(request, f'Błąd podczas kopiowania: {str(e)}')
    else:
        form = CopyTimeSlotsForm()
    
    context = {
        'form': form,
        'title': 'Kopiuj sloty'
    }
    
    return render(request, 'ideas/staff/copy_form.html', context)


@login_required
@user_passes_test(is_staff_user)
def block_slots_view(request):
    """Widok blokowania slotów"""
    if request.method == 'POST':
        form = BlockTimeSlotsForm(request.POST)
        if form.is_valid():
            try:
                services = form.cleaned_data.get('services')
                services_list = list(services) if services else None
                
                result = TimeSlotService.block_slots(
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date'],
                    reason=form.cleaned_data['block_reason'],
                    note=form.cleaned_data.get('block_note', ''),
                    start_time=form.cleaned_data.get('start_time'),
                    end_time=form.cleaned_data.get('end_time'),
                    blocked_by=request.user,
                    services=services_list
                )
                
                if result.get('created_blocks', 0) > 0:
                    messages.success(
                        request,
                        f'Utworzono {result["created_blocks"]} globalnych blokad (wszystkie usługi).'
                    )
                elif result['blocked_count'] > 0:
                    messages.success(
                        request,
                        f'Zablokowano {result["blocked_count"]} slotów.'
                    )
                else:
                    messages.info(request, 'Nie znaleziono slotów do zablokowania.')
                
                if result['with_reservations']:
                    messages.warning(
                        request,
                        f'Pominięto {len(result["with_reservations"])} slotów z rezerwacjami.'
                    )
                
                return redirect('staff_calendar')
                
            except Exception as e:
                messages.error(request, f'Błąd podczas blokowania: {str(e)}')
    else:
        form = BlockTimeSlotsForm()
    
    context = {
        'form': form,
        'title': 'Zablokuj sloty'
    }
    
    return render(request, 'ideas/staff/block_form.html', context)


@login_required
@user_passes_test(is_staff_user)
def slot_list_view(request):
    """Widok listy slotów z filtrowaniem"""
    # Filtry z URL
    service_id = request.GET.get('service')
    status = request.GET.get('status')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    recurring_only = request.GET.get('recurring') == '1'
    
    # Buduj zapytanie
    slots = TimeSlot.objects.select_related('service', 'created_by').prefetch_related(
        'reservation_slot'
    ).order_by('-start')
    
    if service_id:
        slots = slots.filter(service_id=service_id)
    
    if status:
        slots = slots.filter(status=status)
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            slots = slots.filter(start__date__gte=start_date)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            slots = slots.filter(start__date__lte=end_date)
        except ValueError:
            pass
    
    if recurring_only:
        slots = slots.filter(is_recurring=True)
    
    # Paginacja
    paginator = Paginator(slots, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statystyki
    stats = {
        'total': slots.count(),
        'available': slots.filter(status='available').count(),
        'booked': slots.filter(status='booked').count(),
        'blocked': slots.filter(status='blocked').count(),
    }
    
    # Usługi do filtra
    services = Service.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'services': services,
        'selected_service': service_id,
        'selected_status': status,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'recurring_only': recurring_only,
        'stats': stats,
    }
    
    return render(request, 'ideas/staff/slot_list.html', context)


@login_required
@user_passes_test(is_staff_user)
def delete_slot_view(request, slot_id):
    """Usuń pojedynczy slot"""
    slot = get_object_or_404(TimeSlot, pk=slot_id)
    
    if slot.status == 'booked':
        messages.error(request, 'Nie można usunąć zarezerwowanego slotu.')
        return redirect('slot_list')
    
    if request.method == 'POST':
        slot_info = f'{slot.service.name} - {slot.start.strftime("%Y-%m-%d %H:%M")}'
        slot.delete()
        messages.success(request, f'Usunięto slot: {slot_info}')
        return redirect(request.POST.get('next', 'slot_list'))
    
    context = {'slot': slot}
    return render(request, 'ideas/staff/slot_delete_confirm.html', context)


@login_required
@user_passes_test(is_staff_user)
def delete_recurring_group_view(request, group_id):
    """Usuń grupę cyklicznych slotów"""
    slots = TimeSlot.objects.filter(recurring_group_id=group_id)
    
    if not slots.exists():
        messages.error(request, 'Nie znaleziono grupy slotów.')
        return redirect('slot_list')
    
    if request.method == 'POST':
        delete_booked = request.POST.get('delete_booked') == '1'
        
        result = TimeSlotService.delete_recurring_group(
            recurring_group_id=group_id,
            delete_booked=delete_booked
        )
        
        messages.success(
            request,
            f'Usunięto {result["deleted_count"]} slotów z grupy cyklicznej.'
        )
        
        if result['skipped_booked'] > 0:
            messages.warning(
                request,
                f'Pominięto {result["skipped_booked"]} zarezerwowanych slotów.'
            )
        
        return redirect('slot_list')
    
    sample_slot = slots.first()
    booked_count = slots.filter(status='booked').count()
    
    context = {
        'group_id': group_id,
        'total_slots': slots.count(),
        'booked_count': booked_count,
        'sample_slot': sample_slot,
    }
    
    return render(request, 'ideas/staff/recurring_delete_confirm.html', context)


@login_required
@user_passes_test(is_staff_user)
def slot_api_available(request):
    """API endpoint: dostępne sloty dla usługi w danym dniu"""
    service_id = request.GET.get('service')
    date_str = request.GET.get('date')
    
    if not service_id or not date_str:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        service = Service.objects.get(pk=service_id, is_active=True)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Service.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    
    slots = TimeSlotService.get_available_slots(service, date)
    
    slots_data = [
        {
            'id': slot.id,
            'start': slot.start.strftime('%H:%M'),
            'end': slot.end.strftime('%H:%M'),
            'duration': slot.duration_minutes,
        }
        for slot in slots
    ]
    
    return JsonResponse({'slots': slots_data})
