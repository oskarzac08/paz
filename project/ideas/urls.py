from django.urls import path
from django.contrib.auth.views import LoginView
from .views import IdeaListView

app_name = 'ideas'

urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('', IdeaListView.as_view(), name='idea-list'),
]
