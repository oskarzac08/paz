from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Idea
from django.shortcuts import render, redirect
from .forms import PolishUserCreationForm
from django.contrib import messages
from django.utils import timezone


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
            user.save()
            # set activation_date on the user's profile automatically
            try:
                profile = user.profile
                profile.activation_date = timezone.now()
                profile.save()
            except Exception:
                pass
            messages.success(request, 'Konto utworzone. Zaloguj się.')
            return redirect('ideas:login')
    else:
        form = PolishUserCreationForm()
    return render(request, 'register.html', {'form': form})
