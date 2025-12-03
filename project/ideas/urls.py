from django.urls import path
from django.contrib.auth.views import LoginView
from .views import IdeaListView
from .views import landing, register_view
from .views import activate_account

app_name = 'ideas'

urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('', IdeaListView.as_view(), name='idea-list'),
    path('landing/', landing, name='landing'),
    path('register/', register_view, name='register'),
    path('activate/<uuid:uid>/', activate_account, name='activate'),
    path('ideas/', IdeaListView.as_view(), name='idea-list-duplicate'),
]
