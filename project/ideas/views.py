from django.views.generic import ListView
from .models import Idea


class IdeaListView(ListView):
	model = Idea
	template_name = 'ideas/idea_list.html'
	context_object_name = 'ideas'
	paginate_by = 20
