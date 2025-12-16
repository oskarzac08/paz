"""
Serwis historii wizyt i profilu użytkownika

Zgodnie z PDR-008
"""

from django.db.models import Count, Sum, Avg, Q, Max, Min
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class HistoryService:
    """Serwis do zarządzania historią wizyt i statystykami użytkownika"""
    
    @staticmethod
    def get_user_reservations(user, status_filter=None, limit=None):
        """
        Pobiera rezerwacje użytkownika z opcjonalnym filtrowaniem
        
        Args:
            user: User object
            status_filter: 'upcoming', 'past', 'cancelled', 'all'
            limit: Maksymalna liczba wyników
        
        Returns:
            QuerySet rezerwacji
        """
        from .models import Reservation
        
        reservations = Reservation.objects.filter(user=user).select_related('service')
        
        if status_filter == 'upcoming':
            reservations = reservations.filter(
                start__gte=timezone.now(),
                status__in=['pending', 'confirmed']
            ).order_by('start')
        elif status_filter == 'past':
            reservations = reservations.filter(
                Q(start__lt=timezone.now()) | Q(status__in=['completed', 'cancelled', 'no_show'])
            ).order_by('-start')
        elif status_filter == 'cancelled':
            reservations = reservations.filter(
                status__in=['cancelled', 'no_show']
            ).order_by('-start')
        else:  # all
            reservations = reservations.order_by('-start')
        
        if limit:
            reservations = reservations[:limit]
        
        return reservations
    
    @staticmethod
    def get_user_stats(user):
        """
        Oblicza statystyki użytkownika
        
        Returns:
            Dict ze statystykami
        """
        from .models import Reservation
        
        reservations = Reservation.objects.filter(user=user)
        
        # Podstawowe liczniki
        total_count = reservations.count()
        completed_count = reservations.filter(status='completed').count()
        cancelled_count = reservations.filter(status='cancelled').count()
        no_show_count = reservations.filter(status='no_show').count()
        upcoming_count = reservations.filter(
            start__gte=timezone.now(),
            status__in=['pending', 'confirmed']
        ).count()
        
        # Łączne wydatki
        total_spent = reservations.filter(
            status='completed'
        ).aggregate(
            total=Sum('service__price')
        )['total'] or 0
        
        # Ostatnia wizyta
        last_visit = reservations.filter(
            status='completed'
        ).aggregate(
            last=Max('start')
        )['last']
        
        # Pierwsza wizyta (data rejestracji jako klient)
        first_visit = reservations.aggregate(
            first=Min('created_at')
        )['first']
        
        # Ulubiona usługa
        favorite_service = None
        favorite_service_count = 0
        if completed_count > 0:
            favorite_data = reservations.filter(
                status='completed'
            ).values('service__name').annotate(
                count=Count('service')
            ).order_by('-count').first()
            
            if favorite_data:
                favorite_service = favorite_data['service__name']
                favorite_service_count = favorite_data['count']
        
        # Średni interwał między wizytami
        avg_interval = None
        if completed_count >= 2:
            completed_visits = list(reservations.filter(
                status='completed'
            ).order_by('start').values_list('start', flat=True))
            
            intervals = []
            for i in range(1, len(completed_visits)):
                delta = (completed_visits[i] - completed_visits[i-1]).days
                intervals.append(delta)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
        
        # Wskaźniki
        completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0
        cancellation_rate = (cancelled_count / total_count * 100) if total_count > 0 else 0
        no_show_rate = (no_show_count / total_count * 100) if total_count > 0 else 0
        
        # Segment
        segment = user.profile.customer_segment if hasattr(user, 'profile') else 'new'
        segment_badge = user.profile.segment_badge if hasattr(user, 'profile') else '🌟'
        
        # Czas trwania jako klient
        customer_since = first_visit
        if customer_since:
            days_as_customer = (timezone.now() - customer_since).days
            months_as_customer = days_as_customer / 30
        else:
            days_as_customer = 0
            months_as_customer = 0
        
        return {
            'total_count': total_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'no_show_count': no_show_count,
            'upcoming_count': upcoming_count,
            'total_spent': total_spent,
            'last_visit': last_visit,
            'first_visit': first_visit,
            'favorite_service': favorite_service,
            'favorite_service_count': favorite_service_count,
            'avg_interval': avg_interval,
            'completion_rate': completion_rate,
            'cancellation_rate': cancellation_rate,
            'no_show_rate': no_show_rate,
            'segment': segment,
            'segment_badge': segment_badge,
            'days_as_customer': days_as_customer,
            'months_as_customer': months_as_customer,
            'customer_since': customer_since,
        }
    
    @staticmethod
    def get_monthly_stats(user, year=None):
        """
        Oblicza statystyki miesięczne dla wybranego roku
        
        Args:
            user: User object
            year: Rok (domyślnie bieżący)
        
        Returns:
            Lista słowników ze statystykami dla każdego miesiąca
        """
        from .models import Reservation
        
        if year is None:
            year = timezone.now().year
        
        monthly_data = []
        
        for month in range(1, 13):
            month_start = timezone.make_aware(timezone.datetime(year, month, 1))
            
            if month == 12:
                month_end = timezone.make_aware(timezone.datetime(year + 1, 1, 1))
            else:
                month_end = timezone.make_aware(timezone.datetime(year, month + 1, 1))
            
            # Rezerwacje w tym miesiącu
            month_reservations = Reservation.objects.filter(
                user=user,
                start__gte=month_start,
                start__lt=month_end
            )
            
            count = month_reservations.count()
            completed = month_reservations.filter(status='completed').count()
            spent = month_reservations.filter(
                status='completed'
            ).aggregate(
                total=Sum('service__price')
            )['total'] or 0
            
            # Czas (suma duration_minutes)
            total_minutes = 0
            for res in month_reservations.filter(status='completed'):
                if res.service:
                    total_minutes += res.service.duration_minutes
            
            monthly_data.append({
                'month': month,
                'month_name': timezone.datetime(year, month, 1).strftime('%B'),
                'count': count,
                'completed': completed,
                'spent': float(spent),
                'total_hours': total_minutes / 60,
            })
        
        return monthly_data
    
    @staticmethod
    def get_service_distribution(user):
        """
        Zwraca rozkład wizyt po usługach
        
        Returns:
            Lista słowników z nazwą usługi i liczbą wizyt
        """
        from .models import Reservation
        
        distribution = Reservation.objects.filter(
            user=user,
            status='completed'
        ).values('service__name').annotate(
            count=Count('service')
        ).order_by('-count')
        
        return list(distribution)
    
    @staticmethod
    def create_rebook_suggestion(reservation):
        """
        Tworzy sugestię re-bookingu na podstawie poprzedniej wizyty
        
        Args:
            reservation: Poprzednia rezerwacja
        
        Returns:
            Dict z danymi do pre-fill formularza rezerwacji
        """
        return {
            'service_id': reservation.service.id,
            'service_name': reservation.service.name,
            'duration': reservation.service.duration_minutes,
            'price': reservation.service.price,
            'notes': reservation.notes,  # Przeniesienie notatek klienta
        }
    
    @staticmethod
    def get_staff_view_profile(user):
        """
        Zwraca rozszerzony profil klienta dla widoku obsługi
        
        Returns:
            Dict z pełnymi danymi profilu
        """
        stats = HistoryService.get_user_stats(user)
        
        # Ostatnie 5 wizyt
        recent_visits = HistoryService.get_user_reservations(
            user, 
            status_filter='past', 
            limit=5
        )
        
        # Preferowane dni tygodnia (najwięcej wizyt)
        from .models import Reservation
        from django.db.models.functions import ExtractWeekDay
        
        preferred_weekday = Reservation.objects.filter(
            user=user,
            status='completed'
        ).annotate(
            weekday=ExtractWeekDay('start')
        ).values('weekday').annotate(
            count=Count('weekday')
        ).order_by('-count').first()
        
        weekday_names = {
            1: 'Niedziela',
            2: 'Poniedziałek',
            3: 'Wtorek',
            4: 'Środa',
            5: 'Czwartek',
            6: 'Piątek',
            7: 'Sobota',
        }
        
        preferred_day = weekday_names.get(preferred_weekday['weekday']) if preferred_weekday else None
        
        # Preferowane godziny
        from django.db.models.functions import ExtractHour
        
        preferred_hour = Reservation.objects.filter(
            user=user,
            status='completed'
        ).annotate(
            hour=ExtractHour('start')
        ).values('hour').annotate(
            count=Count('hour')
        ).order_by('-count').first()
        
        preferred_time = None
        if preferred_hour:
            hour = preferred_hour['hour']
            if hour < 12:
                preferred_time = 'Ranki'
            elif hour < 17:
                preferred_time = 'Popołudnia'
            else:
                preferred_time = 'Wieczory'
        
        # Notatki obsługi z profilu
        staff_notes = user.profile.staff_notes if hasattr(user, 'profile') else ''
        
        return {
            **stats,
            'recent_visits': recent_visits,
            'preferred_day': preferred_day,
            'preferred_time': preferred_time,
            'staff_notes': staff_notes,
        }
    
    @staticmethod
    def add_staff_note_to_reservation(reservation, note_text, author, is_important=False):
        """
        Dodaje notatkę obsługi do rezerwacji
        
        Args:
            reservation: Reservation object
            note_text: Treść notatki
            author: User object (staff member)
            is_important: Czy notatka jest ważna (alergie, etc.)
        
        Returns:
            ReservationNote object
        """
        from .models import ReservationNote
        
        note = ReservationNote.objects.create(
            reservation=reservation,
            author=author,
            note=note_text,
            is_important=is_important
        )
        
        logger.info(f"Staff note added to reservation {reservation.id} by {author.username}")
        
        return note
    
    @staticmethod
    def update_all_user_stats():
        """
        Aktualizuje statystyki dla wszystkich użytkowników (maintenance task)
        Można uruchomić jako Celery periodic task
        """
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        updated = 0
        
        for user in User.objects.all():
            if hasattr(user, 'profile'):
                try:
                    user.profile.update_stats()
                    updated += 1
                except Exception as e:
                    logger.error(f"Failed to update stats for user {user.id}: {e}")
        
        logger.info(f"Updated stats for {updated} users")
        return updated
