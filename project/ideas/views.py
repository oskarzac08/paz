from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Idea
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from .forms import PolishUserCreationForm
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import ActivationCode


class IdeaListView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    model = Idea
    template_name = 'ideas/idea_list.html'
    context_object_name = 'ideas'
    paginate_by = 20


def landing(request):
    # simple landing page with two buttons: login and register
    return render(request, 'landing.html')


def register_view(request):
    if request.method == 'POST':
        form = PolishUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            # mark as inactive until activation
            user.is_active = False
            user.save()
            # set activation_date on the user's profile automatically
            try:
                profile = user.profile
                profile.activation_date = timezone.now()
                profile.save()
            except Exception:
                pass

            # create activation code and send mail
            expires_at = timezone.now() + timedelta(minutes=settings.ACTIVATION_LINK_EXPIRATION_MINUTES)
            activation_code = ActivationCode.objects.create(user=user, expires_at=expires_at)

            activation_link = request.build_absolute_uri(
                reverse('ideas:activate', args=[str(activation_code.uid)])
            )
            send_mail(
                subject='Aktywacja konta',
                message=(
                    'Dziękujemy za rejestrację. Kliknij poniższy link, aby aktywować konto:\n'
                    f'{activation_link}\n\n'
                    f'Link jest ważny przez {settings.ACTIVATION_LINK_EXPIRATION_MINUTES} minut.'
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )

            messages.success(
                request,
                'Konto utworzone. Sprawdź skrzynkę e-mail i kliknij link, aby aktywować konto.',
            )
            return redirect('ideas:login')
    else:
        form = PolishUserCreationForm()
    return render(request, 'register.html', {'form': form})


def activate_account(request, uid):
    try:
        activation_code = ActivationCode.objects.select_related('user').get(uid=uid)
    except ActivationCode.DoesNotExist:
        messages.error(request, 'Link jest nieważny lub nie istnieje.')
        return redirect('ideas:login')

    if activation_code.is_used:
        messages.info(request, 'Konto było już wcześniej aktywowane z tego linku.')
        return redirect('ideas:login')

    if timezone.now() > activation_code.expires_at:
        messages.error(request, 'Link jest nieważny (upłynął czas na aktywację).')
        return redirect('ideas:login')

    user = activation_code.user
    user.is_active = True
    user.save(update_fields=['is_active'])

    profile = getattr(user, 'profile', None)
    if profile is not None:
        profile.activation_date = timezone.now()
        profile.save(update_fields=['activation_date'])

    activation_code.mark_used()
    messages.success(request, 'Konto zostało pomyślnie aktywowane.')
    return redirect('ideas:login')
