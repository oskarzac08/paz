from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Idea


class IdeaListView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    model = Idea
    template_name = 'ideas/idea_list.html'
    context_object_name = 'ideas'
    paginate_by = 20
