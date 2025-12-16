"""
Widoki dla systemu powiadomień

Zarządzanie preferencjami użytkownika
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .models import NotificationPreference


@login_required
@require_http_methods(["GET", "POST"])
def notification_preferences(request):
    """
    Widok do zarządzania preferencjami powiadomień użytkownika
    """
    # Pobierz lub utwórz preferencje
    prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Aktualizuj preferencje
        prefs.preferred_channel = request.POST.get('preferred_channel', 'email')
        
        # Przypomnienia (checkboxy)
        prefs.enable_reminder_24h = request.POST.get('enable_reminder_24h') == 'on'
        prefs.enable_reminder_2h = request.POST.get('enable_reminder_2h') == 'on'
        
        # Zmiany
        prefs.enable_booking_changes = request.POST.get('enable_booking_changes') == 'on'
        
        # Marketing
        prefs.enable_marketing = request.POST.get('enable_marketing') == 'on'
        prefs.enable_newsletter = request.POST.get('enable_newsletter') == 'on'
        
        # Godziny ciszy
        quiet_start = request.POST.get('quiet_hours_start')
        quiet_end = request.POST.get('quiet_hours_end')
        
        if quiet_start:
            prefs.quiet_hours_start = quiet_start
        else:
            prefs.quiet_hours_start = None
            
        if quiet_end:
            prefs.quiet_hours_end = quiet_end
        else:
            prefs.quiet_hours_end = None
        
        prefs.save()
        
        messages.success(request, 'Preferencje powiadomień zostały zaktualizowane.')
        return redirect('notification_preferences')
    
    context = {
        'preferences': prefs,
    }
    
    return render(request, 'notifications/preferences.html', context)


@login_required
def notification_history(request):
    """
    Historia powiadomień użytkownika
    """
    from .models import Notification
    
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]  # Ostatnie 50
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'notifications/history.html', context)
