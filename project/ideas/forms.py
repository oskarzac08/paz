from django import forms
from django.forms import inlineformset_factory
from .models import Idea, IdeaImage
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Login")
    password = forms.CharField(widget=forms.PasswordInput, label="Hasło")


class PolishUserCreationForm(UserCreationForm):
    email = forms.EmailField(label="Adres e-mail", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nazwa użytkownika'
        self.fields['password1'].label = 'Hasło'
        self.fields['password2'].label = 'Powtórz hasło'
        self.fields['email'].help_text = 'Wprowadź prawidłowy adres e-mail.'


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
