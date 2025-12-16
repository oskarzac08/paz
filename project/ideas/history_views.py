"""
Views for user history and profile management (PDR-008).

This module implements:
- User profile dashboard with statistics
- Reservation history with filtering
- Detailed reservation view with re-booking
- User statistics and charts
- Staff view of client profiles
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from datetime import datetime, timedelta

from .models import Reservation, UserProfile, Service, ReservationNote
from .history_service import HistoryService


@login_required
def my_profile(request):
    """
    User profile dashboard (Profil użytkownika).
    
    Displays:
    - User statistics (total visits, cancellations, spending)
    - Customer segment badge
    - Favorite service
    - Recent reservations
    - Quick actions
    """
    history_service = HistoryService()
    
    # Get user statistics
    stats = history_service.get_user_stats(request.user)
    
    # Get recent reservations (last 5)
    recent_reservations = history_service.get_user_reservations(
        request.user,
        status_filter='all',
        limit=5
    )
    
    # Update user stats in background (if needed)
    profile = UserProfile.objects.get(user=request.user)
    if not profile.last_visit_date or (
        timezone.now() - profile.last_visit_date > timedelta(days=1)
    ):
        profile.update_stats()
        profile.update_segment()
    
    context = {
        'stats': stats,
        'recent_reservations': recent_reservations,
        'profile': profile,
        'segment_badge': profile.segment_badge,
    }
    
    return render(request, 'history/profile_dashboard.html', context)


@login_required
def my_reservations(request):
    """
    User reservation history (Historia wizyt).
    
    Features:
    - Filterable list (upcoming, past, cancelled, all)
    - Search by service name
    - Pagination
    - Quick re-book option
    """
    history_service = HistoryService()
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Get reservations
    reservations = history_service.get_user_reservations(
        request.user,
        status_filter=status_filter
    )
    
    # Apply search filter
    if search_query:
        reservations = reservations.filter(
            Q(service__name__icontains=search_query) |
            Q(service__category__name__icontains=search_query)
        )
    
    # Count by status for filter badges
    all_reservations = Reservation.objects.filter(user=request.user)
    filter_counts = {
        'all': all_reservations.count(),
        'upcoming': all_reservations.filter(
            start__gte=timezone.now()
        ).exclude(status='cancelled').count(),
        'past': all_reservations.filter(
            start__lt=timezone.now(),
            status='completed'
        ).count(),
        'cancelled': all_reservations.filter(status='cancelled').count(),
    }
    
    context = {
        'reservations': reservations,
        'status_filter': status_filter,
        'search_query': search_query,
        'filter_counts': filter_counts,
    }
    
    return render(request, 'history/reservation_history.html', context)


@login_required
def reservation_detail(request, reservation_id):
    """
    Detailed reservation view (Szczegóły wizyty).
    
    Features:
    - Full reservation information
    - Service details
    - Staff notes (if available)
    - Re-book button
    - Cancel option (if applicable)
    """
    reservation = get_object_or_404(
        Reservation,
        id=reservation_id,
        user=request.user
    )
    
    history_service = HistoryService()
    
    # Generate re-book suggestion
    rebook_data = history_service.create_rebook_suggestion(reservation)
    
    # Check if reservation can be cancelled
    can_cancel = (
        reservation.status in ['pending', 'confirmed'] and
        reservation.start >= timezone.now()
    )
    
    # Get staff notes (visible only to staff, but we prepare the count)
    staff_notes_count = ReservationNote.objects.filter(
        reservation=reservation
    ).count()
    
    context = {
        'reservation': reservation,
        'rebook_data': rebook_data,
        'can_cancel': can_cancel,
        'staff_notes_count': staff_notes_count,
    }
    
    return render(request, 'history/reservation_detail.html', context)


@login_required
def rebook_service(request, reservation_id):
    """
    Quick re-booking (Ponowna rezerwacja).
    
    Pre-fills booking form with data from previous reservation.
    Redirects to booking page with service pre-selected.
    """
    reservation = get_object_or_404(
        Reservation,
        id=reservation_id,
        user=request.user
    )
    
    history_service = HistoryService()
    rebook_data = history_service.create_rebook_suggestion(reservation)
    
    # Store re-book data in session
    request.session['rebook_service_id'] = rebook_data['service_id']
    request.session['rebook_from_reservation'] = reservation_id
    
    messages.success(
        request,
        f'Przygotowano rezerwację usługi: {rebook_data["service_name"]}'
    )
    
    # Redirect to booking page (service selection or timeslot)
    return redirect('ideas:book_service', service_id=rebook_data['service_id'])


@login_required
def my_statistics(request):
    """
    User statistics dashboard (Statystyki użytkownika).
    
    Displays:
    - Monthly visit/spending chart (current year)
    - Service distribution (favorite services)
    - Visit frequency analysis
    - Year selector for historical data
    """
    history_service = HistoryService()
    
    # Get selected year (default: current year)
    selected_year = int(request.GET.get('year', timezone.now().year))
    
    # Get monthly statistics
    monthly_stats = history_service.get_monthly_stats(request.user, selected_year)
    
    # Get service distribution
    service_distribution = history_service.get_service_distribution(request.user)
    
    # Get overall stats
    stats = history_service.get_user_stats(request.user)
    
    # Get available years (years with reservations)
    available_years = Reservation.objects.filter(
        user=request.user
    ).dates('start__date', 'year', order='DESC')
    available_years = [d.year for d in available_years]
    
    if not available_years:
        available_years = [timezone.now().year]
    
    context = {
        'monthly_stats': monthly_stats,
        'service_distribution': service_distribution,
        'stats': stats,
        'selected_year': selected_year,
        'available_years': available_years,
    }
    
    return render(request, 'history/user_statistics.html', context)


@login_required
def statistics_api(request):
    """
    API endpoint for statistics data (for charts).
    
    Returns JSON data for:
    - Monthly visits/spending
    - Service distribution
    
    Used by JavaScript charting libraries.
    """
    history_service = HistoryService()
    
    chart_type = request.GET.get('type', 'monthly')
    year = int(request.GET.get('year', timezone.now().year))
    
    if chart_type == 'monthly':
        data = history_service.get_monthly_stats(request.user, year)
    elif chart_type == 'services':
        data = history_service.get_service_distribution(request.user)
    else:
        data = {'error': 'Invalid chart type'}
    
    return JsonResponse(data, safe=False)


# ============================================================================
# STAFF VIEWS
# ============================================================================

@login_required
def staff_client_profile(request, user_id):
    """
    Staff view of client profile (Widok obsługi - profil klienta).
    
    Accessible only to staff members.
    
    Displays:
    - Extended client statistics
    - Visit history with staff notes
    - Customer segment and risk analysis
    - Preferences (favorite services, time slots, weekdays)
    - Note management
    """
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'Brak uprawnień do tej strony.')
        return redirect('ideas:index')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    client = get_object_or_404(User, id=user_id)
    history_service = HistoryService()
    
    # Get extended profile data
    profile_data = history_service.get_staff_view_profile(client)
    
    # Get recent reservations with notes
    recent_reservations = history_service.get_user_reservations(
        client,
        status_filter='all',
        limit=10
    )
    
    # Get all staff notes for this client
    all_notes = ReservationNote.objects.filter(
        reservation__user=client
    ).select_related('reservation', 'author').order_by('-created_at')[:20]
    
    context = {
        'client': client,
        'profile_data': profile_data,
        'recent_reservations': recent_reservations,
        'all_notes': all_notes,
    }
    
    return render(request, 'history/staff_client_profile.html', context)


@login_required
@csrf_protect
def add_staff_note(request, reservation_id):
    """
    Add staff note to reservation.
    
    POST only. Accessible only to staff.
    """
    if not request.user.is_staff:
        messages.error(request, 'Brak uprawnień.')
        return redirect('ideas:index')
    
    if request.method != 'POST':
        messages.error(request, 'Nieprawidłowa metoda.')
        return redirect('ideas:index')
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    note_text = request.POST.get('note', '').strip()
    is_important = request.POST.get('is_important') == 'true'
    
    if not note_text:
        messages.error(request, 'Treść notatki jest wymagana.')
        return redirect('ideas:staff_client_profile', user_id=reservation.user.id)
    
    history_service = HistoryService()
    note = history_service.add_staff_note_to_reservation(
        reservation=reservation,
        author=request.user,
        note=note_text,
        is_important=is_important
    )
    
    # Update profile segment after adding note (might affect segmentation)
    profile = UserProfile.objects.get(user=reservation.user)
    profile.update_segment()
    
    messages.success(request, 'Notatka została dodana.')
    return redirect('ideas:staff_client_profile', user_id=reservation.user.id)


@login_required
def update_client_segment(request, user_id):
    """
    Manually trigger segment update for client.
    
    Staff only. Useful for forcing recalculation.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    client = get_object_or_404(User, id=user_id)
    profile = UserProfile.objects.get(user=client)
    
    # Update stats and segment
    profile.update_stats()
    profile.update_segment()
    
    messages.success(
        request,
        f'Segment zaktualizowany: {profile.get_customer_segment_display()}'
    )
    
    return redirect('ideas:staff_client_profile', user_id=user_id)
