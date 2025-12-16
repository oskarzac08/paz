from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import (
    IdeaListView, 
    landing, 
    register_view,
    verify_code_view,
    resend_verification_code,
    verification_status_view
)
from . import views
from . import booking_views
from . import cancellation_views
from . import catalog_views
from . import timeslot_views
from . import notification_views
from . import history_views

app_name = 'ideas'

urlpatterns = [
    path('', views.home, name='home'),
    path('landing/', landing, name='landing'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='ideas:landing'), name='logout'),
    path('register/', register_view, name='register'),
    path('verify/', verify_code_view, name='verify_code'),
    path('resend/', resend_verification_code, name='resend_code'),
    path('verification-status/', verification_status_view, name='verification_status'),
    # Simple API endpoints for email code request/confirm
    path('auth/request-code/', views.request_email_code, name='api_request_code'),
    path('auth/confirm-code/', views.confirm_email_code, name='api_confirm_code'),
    # Service catalog
    path('uslugi/', catalog_views.service_catalog_view, name='service_catalog'),
    path('uslugi/<int:service_id>/', catalog_views.service_detail_view, name='service_detail'),
    path('api/uslugi/', catalog_views.service_api_list, name='service_api_list'),
    # Staff: Time Management
    path('staff/kalendarz/', timeslot_views.staff_calendar_view, name='staff_calendar'),
    path('staff/slot/utworz/', timeslot_views.create_single_slot_view, name='create_single_slot'),
    path('staff/slot/cykliczne/', timeslot_views.create_recurring_slots_view, name='create_recurring_slots'),
    path('staff/slot/szablon/<int:template_id>/', timeslot_views.apply_template_view, name='apply_template'),
    path('staff/slot/kopiuj/', timeslot_views.copy_slots_view, name='copy_slots'),
    path('staff/slot/zablokuj/', timeslot_views.block_slots_view, name='block_slots'),
    path('staff/slot/lista/', timeslot_views.slot_list_view, name='slot_list'),
    path('staff/slot/usun/<int:slot_id>/', timeslot_views.delete_slot_view, name='delete_slot'),
    path('staff/slot/usun-gruppe/<str:group_id>/', timeslot_views.delete_recurring_group_view, name='delete_recurring_group'),
    path('api/staff/sloty-dostepne/', timeslot_views.slot_api_available, name='slot_api_available'),
    # Dev-only endpoint to return current CSRF token
    path('dev/csrf/', views.dev_csrf_view, name='dev_csrf'),
    # New Booking flow (5 steps)
    path('rezerwacja/', booking_views.booking_step1_service, name='booking_step1_service'),
    path('rezerwacja/regulamin/', booking_views.booking_step2_terms, name='booking_step2_terms'),
    path('rezerwacja/kalendarz/', booking_views.booking_step3_calendar, name='booking_step3_calendar'),
    path('rezerwacja/dostepne-godziny/', booking_views.get_available_time_slots, name='available_time_slots'),
    path('rezerwacja/dostepne-dni/', booking_views.get_available_days, name='available_days'),
    path('rezerwacja/dane/', booking_views.booking_step4_auth, name='booking_step4_auth'),
    path('rezerwacja/potwierdzenie/', booking_views.booking_step5_confirm, name='booking_step5_confirm'),
    path('rezerwacja/sukces/<int:reservation_id>/', booking_views.booking_success, name='booking_success'),
    # Cancellation flow
    path('moje-wizyty/', cancellation_views.my_reservations, name='my_reservations'),
    path('odwolaj/<int:reservation_id>/', cancellation_views.cancel_reservation, name='cancel_reservation'),
    path('odwolaj/token/<str:token>/', cancellation_views.cancel_with_token, name='cancel_with_token'),
    path('odwolaj/sukces/<int:reservation_id>/', cancellation_views.cancellation_success, name='cancellation_success'),
    # Notifications
    path('powiadomienia/ustawienia/', notification_views.notification_preferences, name='notification_preferences'),
    path('powiadomienia/historia/', notification_views.notification_history, name='notification_history'),
    # History & Profile (PDR-008)
    path('profil/', history_views.my_profile, name='my_profile'),
    path('historia/', history_views.my_reservations, name='my_reservations'),
    path('rezerwacja/<int:reservation_id>/szczegoly/', history_views.reservation_detail, name='reservation_detail'),
    path('rezerwacja/<int:reservation_id>/ponow/', history_views.rebook_service, name='rebook_service'),
    path('statystyki/', history_views.my_statistics, name='my_statistics'),
    path('api/statystyki/', history_views.statistics_api, name='statistics_api'),
    # Staff views for client profiles
    path('staff/klient/<int:user_id>/', history_views.staff_client_profile, name='staff_client_profile'),
    path('staff/notatka/<int:reservation_id>/', history_views.add_staff_note, name='add_staff_note'),
    path('staff/klient/<int:user_id>/aktualizuj-segment/', history_views.update_client_segment, name='update_client_segment'),
    # Old booking flow (deprecated)
    path('booking/service/', views.booking_step_service, name='booking_service'),
    path('booking/datetime/', views.booking_step_datetime, name='booking_datetime'),
    path('booking/summary/', views.booking_step_summary, name='booking_summary'),
    path('booking/confirm/', views.booking_step_confirm, name='booking_confirm'),
]
