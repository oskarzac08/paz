from django import forms
from django.forms import inlineformset_factory
from .models import Idea, IdeaImage
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Login")
    password = forms.CharField(widget=forms.PasswordInput, label="Hasło")


class PolishUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label="Adres e-mail", 
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'To pole jest wymagane.',
            'invalid': 'Wprowadź prawidłowy adres e-mail.',
        }
    )
    phone_number = forms.CharField(
        label="Numer telefonu",
        max_length=15,
        required=False,
        help_text="Format: +48123456789 (opcjonalnie)",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'max_length': 'Numer telefonu jest zbyt długi.',
        }
    )
    preferred_contact = forms.ChoiceField(
        label="Preferowany kanał weryfikacji",
        choices=[('email', 'E-mail'), ('sms', 'SMS'), ('both', 'Oba')],
        initial='email',
        widget=forms.RadioSelect,
        error_messages={
            'required': 'Wybierz preferowany kanał weryfikacji.',
            'invalid_choice': 'Wybierz prawidłową opcję.',
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nazwa użytkownika'
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].error_messages = {
            'required': 'To pole jest wymagane.',
            'unique': 'Użytkownik o takiej nazwie już istnieje.',
            'invalid': 'Wprowadź prawidłową nazwę użytkownika.',
        }
        self.fields['password1'].label = 'Hasło'
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = None
        self.fields['password1'].error_messages = {
            'required': 'To pole jest wymagane.',
        }
        self.fields['password2'].label = 'Powtórz hasło'
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].help_text = None
        self.fields['password2'].error_messages = {
            'required': 'To pole jest wymagane.',
        }
        self.fields['email'].help_text = 'Wprowadź prawidłowy adres e-mail.'
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Podane hasła nie są identyczne.')
        return password2
    
    def _post_clean(self):
        super()._post_clean()
        # Zamień angielskie błędy walidacji hasła na polskie
        if 'password2' in self.errors:
            polish_errors = []
            for error in self.errors['password2']:
                error_str = str(error)
                if 'do not match' in error_str.lower() or 'didn\'t match' in error_str.lower():
                    polish_errors.append('Podane hasła nie są identyczne.')
                else:
                    polish_errors.append(error_str)
            if polish_errors:
                self.errors['password2'] = polish_errors
        
        if 'password1' in self.errors:
            polish_errors = []
            for error in self.errors['password1']:
                error_str = str(error)
                # Tłumaczenie popularnych błędów
                if 'too similar' in error_str.lower():
                    polish_errors.append('Hasło jest zbyt podobne do innych danych osobowych.')
                elif 'too short' in error_str.lower():
                    polish_errors.append('Hasło musi zawierać co najmniej 8 znaków.')
                elif 'too common' in error_str.lower():
                    polish_errors.append('Hasło jest zbyt popularne.')
                elif 'entirely numeric' in error_str.lower():
                    polish_errors.append('Hasło nie może składać się wyłącznie z cyfr.')
                elif 'required' in error_str.lower():
                    polish_errors.append('To pole jest wymagane.')
                else:
                    polish_errors.append(error_str)
            if polish_errors:
                self.errors['password1'] = polish_errors

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError('Użytkownik z takim adresem e-mail już istnieje.')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Usuń białe znaki
            phone = phone.strip()
            # Walidacja formatu
            if not re.match(r'^\+?[0-9]{9,15}$', phone):
                raise forms.ValidationError(
                    'Wprowadź prawidłowy numer telefonu (9-15 cyfr, opcjonalnie z +)'
                )
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        preferred_contact = cleaned_data.get('preferred_contact')
        phone_number = cleaned_data.get('phone_number')
        
        # Jeśli preferowany kontakt to SMS lub oba, telefon jest wymagany
        if preferred_contact in ['sms', 'both'] and not phone_number:
            raise forms.ValidationError(
                'Numer telefonu jest wymagany dla weryfikacji SMS'
            )
        
        return cleaned_data


class VerificationCodeForm(forms.Form):
    """Formularz do wprowadzania kodu weryfikacyjnego"""
    code = forms.CharField(
        label="Kod weryfikacyjny",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '000000',
            'class': 'form-control text-center',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}'
        }),
        help_text="Wprowadź 6-cyfrowy kod otrzymany w wiadomości"
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.isdigit():
            raise forms.ValidationError('Kod musi składać się tylko z cyfr')
        return code


class ResendCodeForm(forms.Form):
    """Formularz do ponownego wysłania kodu"""
    channel = forms.ChoiceField(
        label="Kanał weryfikacji",
        choices=[('email', 'E-mail'), ('sms', 'SMS')],
        widget=forms.RadioSelect
    )


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
