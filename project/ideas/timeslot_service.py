"""
Service layer for TimeSlot management
Handles creation of single, recurring slots, copying and blocking
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, time
import uuid

from .models import TimeSlot, Service, RecurringSlotTemplate


class TimeSlotService:
    """Serwis zarządzania slotami czasowymi"""
    
    @staticmethod
    def create_single_slot(service, start_dt, duration_minutes=None, created_by=None, status='available'):
        """
        Tworzy pojedynczy slot czasowy
        
        Args:
            service: Obiekt Service
            start_dt: datetime rozpoczęcia
            duration_minutes: czas trwania w minutach (domyślnie z usługi)
            created_by: User który tworzy slot
            status: status slotu (available/blocked)
        
        Returns:
            TimeSlot object
        """
        if duration_minutes is None:
            duration_minutes = service.duration_minutes
        
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Sprawdź nakładające się sloty
        conflicts = TimeSlot.objects.filter(
            service=service,
            start__lt=end_dt,
            end__gt=start_dt
        )
        
        if conflicts.exists():
            raise ValidationError(
                f"Istnieją już sloty w tym czasie: {', '.join([str(s) for s in conflicts])}"
            )
        
        slot = TimeSlot.objects.create(
            service=service,
            start=start_dt,
            end=end_dt,
            status=status,
            created_by=created_by
        )
        
        return slot
    
    @staticmethod
    @transaction.atomic
    def create_recurring_slots(
        service,
        start_date,
        end_date,
        days_of_week,
        start_time,
        end_time,
        slot_interval_minutes=None,
        breaks=None,
        created_by=None,
        template=None
    ):
        """
        Tworzy cykliczne sloty na określony okres
        
        Args:
            service: Obiekt Service
            start_date: data rozpoczęcia (date object)
            end_date: data zakończenia (date object)
            days_of_week: lista dni tygodnia [0=pon, 1=wt, ..., 6=nie]
            start_time: godzina rozpoczęcia (time object)
            end_time: godzina zakończenia (time object)
            slot_interval_minutes: interwał między slotami (domyślnie z usługi)
            breaks: lista przerw [{"start": time, "end": time, "name": str}]
            created_by: User który tworzy sloty
            template: RecurringSlotTemplate (opcjonalnie)
        
        Returns:
            dict: {
                'created_count': int,
                'skipped_count': int,
                'slots': [TimeSlot, ...],
                'recurring_group_id': str
            }
        """
        if slot_interval_minutes is None:
            slot_interval_minutes = service.duration_minutes
        
        if breaks is None:
            breaks = []
        
        # Generuj unikalny ID grupy
        recurring_group_id = str(uuid.uuid4())
        
        created_slots = []
        skipped_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Sprawdź czy to właściwy dzień tygodnia (0=pon, 6=nie)
            if current_date.weekday() in days_of_week:
                # Generuj sloty dla tego dnia
                day_slots = TimeSlotService._generate_slots_for_day(
                    service=service,
                    date=current_date,
                    start_time=start_time,
                    end_time=end_time,
                    slot_interval_minutes=slot_interval_minutes,
                    breaks=breaks,
                    created_by=created_by,
                    recurring_group_id=recurring_group_id,
                    template=template
                )
                
                for slot_data in day_slots:
                    try:
                        slot = TimeSlot.objects.create(**slot_data)
                        created_slots.append(slot)
                    except Exception as e:
                        # Skip conflicting slots
                        skipped_count += 1
            
            current_date += timedelta(days=1)
        
        return {
            'created_count': len(created_slots),
            'skipped_count': skipped_count,
            'slots': created_slots,
            'recurring_group_id': recurring_group_id
        }
    
    @staticmethod
    def _generate_slots_for_day(
        service,
        date,
        start_time,
        end_time,
        slot_interval_minutes,
        breaks,
        created_by=None,
        recurring_group_id=None,
        template=None
    ):
        """Generuje sloty dla pojedynczego dnia"""
        slots = []
        current_time = start_time
        
        while current_time < end_time:
            slot_start_dt = timezone.make_aware(
                datetime.combine(date, current_time)
            )
            slot_end_dt = slot_start_dt + timedelta(minutes=service.duration_minutes)
            
            # Sprawdź czy slot mieści się w godzinach pracy
            if slot_end_dt.time() > end_time:
                break
            
            # Sprawdź czy slot nie koliduje z przerwą
            is_in_break = False
            for break_info in breaks:
                break_start = break_info.get('start')
                break_end = break_info.get('end')
                
                # Konwertuj stringi na time objects jeśli potrzeba
                if isinstance(break_start, str):
                    break_start = datetime.strptime(break_start, '%H:%M').time()
                if isinstance(break_end, str):
                    break_end = datetime.strptime(break_end, '%H:%M').time()
                
                # Sprawdź nakładanie
                if not (slot_end_dt.time() <= break_start or current_time >= break_end):
                    is_in_break = True
                    break
            
            if not is_in_break:
                slot_data = {
                    'service': service,
                    'start': slot_start_dt,
                    'end': slot_end_dt,
                    'status': 'available',
                    'created_by': created_by,
                    'is_recurring': bool(recurring_group_id),
                    'recurring_group_id': recurring_group_id or '',
                    'template': template,
                }
                slots.append(slot_data)
            
            # Następny slot
            temp_dt = datetime.combine(date, current_time)
            temp_dt += timedelta(minutes=slot_interval_minutes)
            current_time = temp_dt.time()
        
        return slots
    
    @staticmethod
    @transaction.atomic
    def copy_slots(source_start_date, source_end_date, target_start_date, copy_blocked=False, skip_existing=True):
        """
        Kopiuje sloty z jednego okresu na drugi
        
        Args:
            source_start_date: data rozpoczęcia źródłowego okresu
            source_end_date: data zakończenia źródłowego okresu
            target_start_date: data rozpoczęcia docelowego okresu
            copy_blocked: czy kopiować zablokowane sloty
            skip_existing: czy pomijać już istniejące sloty
        
        Returns:
            dict: {'created_count': int, 'skipped_count': int}
        """
        # Oblicz przesunięcie czasu
        time_offset = target_start_date - source_start_date
        
        # Pobierz sloty do skopiowania
        source_slots = TimeSlot.objects.filter(
            start__date__gte=source_start_date,
            start__date__lte=source_end_date
        )
        
        if not copy_blocked:
            source_slots = source_slots.exclude(status='blocked')
        
        created_count = 0
        skipped_count = 0
        
        for source_slot in source_slots:
            new_start = source_slot.start + time_offset
            new_end = source_slot.end + time_offset
            
            # Sprawdź czy już istnieje
            if skip_existing:
                exists = TimeSlot.objects.filter(
                    service=source_slot.service,
                    start=new_start,
                    end=new_end
                ).exists()
                
                if exists:
                    skipped_count += 1
                    continue
            
            # Utwórz kopię
            TimeSlot.objects.create(
                service=source_slot.service,
                start=new_start,
                end=new_end,
                status='available' if source_slot.status == 'available' else source_slot.status,
                block_reason=source_slot.block_reason if source_slot.status == 'blocked' else '',
                block_note=source_slot.block_note if source_slot.status == 'blocked' else '',
                created_by=source_slot.created_by,
                is_recurring=False,  # Kopie nie są recurring
                recurring_group_id='',
                template=None
            )
            created_count += 1
        
        return {
            'created_count': created_count,
            'skipped_count': skipped_count
        }
    
    @staticmethod
    @transaction.atomic
    def block_slots(start_date, end_date, reason='other', note='', start_time=None, end_time=None, blocked_by=None, services=None):
        """
        Blokuje sloty w określonym okresie
        
        Args:
            start_date: data rozpoczęcia
            end_date: data zakończenia
            reason: powód blokady
            note: notatka
            start_time: opcjonalna godzina rozpoczęcia (dla blokady częściowej)
            end_time: opcjonalna godzina zakończenia (dla blokady częściowej)
            blocked_by: User blokujący
            services: lista usług do zablokowania (None = blokada globalna bez usługi)
        
        Returns:
            dict: {'blocked_count': int, 'with_reservations': [TimeSlot, ...], 'created_blocks': int}
        """
        blocked_count = 0
        with_reservations = []
        created_blocks = 0
        
        # Jeśli services=None, tworzymy globalną blokadę bez usługi
        if services is None:
            # Tworzymy blokady dla każdego dnia w zakresie
            current_date = start_date
            while current_date <= end_date:
                block_start_time = start_time if start_time else time(0, 0)
                block_end_time = end_time if end_time else time(23, 59)
                
                block_start_dt = timezone.make_aware(
                    datetime.combine(current_date, block_start_time)
                )
                block_end_dt = timezone.make_aware(
                    datetime.combine(current_date, block_end_time)
                )
                
                # Utwórz blokadę bez usługi
                TimeSlot.objects.create(
                    service=None,  # Globalna blokada
                    start=block_start_dt,
                    end=block_end_dt,
                    status='blocked',
                    block_reason=reason,
                    block_note=note,
                    created_by=blocked_by
                )
                created_blocks += 1
                current_date += timedelta(days=1)
        else:
            # Blokuj istniejące sloty dla wybranych usług
            slots_query = TimeSlot.objects.filter(
                start__date__gte=start_date,
                start__date__lte=end_date,
                status='available'
            )
            
            slots_query = slots_query.filter(service__in=services)
            
            if start_time:
                slots_query = slots_query.filter(start__time__gte=start_time)
            
            if end_time:
                slots_query = slots_query.filter(end__time__lte=end_time)
            
            for slot in slots_query:
                # Sprawdź czy slot ma rezerwację
                if hasattr(slot, 'reservation_slot') and slot.reservation_slot.exists():
                    with_reservations.append(slot)
                    continue
                
                slot.block(reason=reason, note=note, blocked_by=blocked_by)
                blocked_count += 1
        
        return {
            'blocked_count': blocked_count,
            'with_reservations': with_reservations,
            'created_blocks': created_blocks
        }
    
    @staticmethod
    @transaction.atomic
    def delete_recurring_group(recurring_group_id, delete_booked=False):
        """
        Usuwa grupę cyklicznych slotów
        
        Args:
            recurring_group_id: UUID grupy
            delete_booked: czy usuwać zajęte sloty (z rezerwacjami)
        
        Returns:
            dict: {'deleted_count': int, 'skipped_booked': int}
        """
        slots = TimeSlot.objects.filter(recurring_group_id=recurring_group_id)
        
        deleted_count = 0
        skipped_booked = 0
        
        for slot in slots:
            if slot.status == 'booked' and not delete_booked:
                skipped_booked += 1
                continue
            
            slot.delete()
            deleted_count += 1
        
        return {
            'deleted_count': deleted_count,
            'skipped_booked': skipped_booked
        }
    
    @staticmethod
    def get_available_slots(service, date, exclude_past=True):
        """
        Zwraca dostępne sloty dla usługi w danym dniu
        
        Args:
            service: Obiekt Service
            date: data (date object)
            exclude_past: czy wykluczyć sloty z przeszłości
        
        Returns:
            QuerySet TimeSlot
        """
        slots = TimeSlot.objects.filter(
            service=service,
            start__date=date,
            status='available'
        )
        
        if exclude_past:
            slots = slots.filter(start__gt=timezone.now())
        
        return slots.order_by('start')
    
    @staticmethod
    def apply_template(template, start_date, end_date, created_by=None):
        """
        Aplikuje szablon cyklicznych slotów
        
        Args:
            template: RecurringSlotTemplate
            start_date: data rozpoczęcia
            end_date: data zakończenia
            created_by: User tworzący sloty
        
        Returns:
            dict: wynik z create_recurring_slots
        """
        # Mapowanie pól template na dni tygodnia
        days_of_week = []
        day_fields = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday',
        }
        
        for day_num, field_name in day_fields.items():
            if getattr(template, field_name):
                days_of_week.append(day_num)
        
        return TimeSlotService.create_recurring_slots(
            service=template.service,
            start_date=start_date,
            end_date=end_date,
            days_of_week=days_of_week,
            start_time=template.start_time,
            end_time=template.end_time,
            slot_interval_minutes=template.slot_interval_minutes,
            breaks=template.breaks,
            created_by=created_by,
            template=template
        )
