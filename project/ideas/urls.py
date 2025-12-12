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

app_name = 'ideas'

urlpatterns = [
    path('', landing, name='landing'),
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
]
