from django import forms
from django.forms import inlineformset_factory
from .models import Idea, IdeaImage
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Login")
    password = forms.CharField(widget=forms.PasswordInput, label="Hasło")


class IdeaForm(forms.ModelForm):
    class Meta:
        model = Idea
        fields = ['title', 'description']


class IdeaImageForm(forms.ModelForm):
    class Meta:
        model = IdeaImage
        fields = ['image']


IdeaImageFormSet = inlineformset_factory(
    Idea,
    IdeaImage,
    form=IdeaImageForm,
    extra=1,
    can_delete=True
)
