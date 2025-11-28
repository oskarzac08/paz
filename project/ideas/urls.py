from django.urls import path
from .views import IdeaListView

app_name = 'ideas'

urlpatterns = [
    path('', IdeaListView.as_view(), name='idea-list'),
]
