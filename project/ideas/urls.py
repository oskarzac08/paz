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
    path('ideas/', IdeaListView.as_view(), name='idea_list'),
    # Dev-only endpoint to return current CSRF token
    path('dev/csrf/', views.dev_csrf_view, name='dev_csrf'),
    # New Booking flow (5 steps)
    path('rezerwacja/', booking_views.booking_step1_service, name='booking_step1_service'),
    path('rezerwacja/regulamin/', booking_views.booking_step2_terms, name='booking_step2_terms'),
    path('rezerwacja/kalendarz/', booking_views.booking_step3_calendar, name='booking_step3_calendar'),
    path('rezerwacja/dostepne-godziny/', booking_views.get_available_time_slots, name='available_time_slots'),
    path('rezerwacja/dane/', booking_views.booking_step4_auth, name='booking_step4_auth'),
    path('rezerwacja/potwierdzenie/', booking_views.booking_step5_confirm, name='booking_step5_confirm'),
    path('rezerwacja/sukces/<int:reservation_id>/', booking_views.booking_success, name='booking_success'),
    # Old booking flow (deprecated)
    path('booking/service/', views.booking_step_service, name='booking_service'),
    path('booking/datetime/', views.booking_step_datetime, name='booking_datetime'),
    path('booking/summary/', views.booking_step_summary, name='booking_summary'),
    path('booking/confirm/', views.booking_step_confirm, name='booking_confirm'),
]
