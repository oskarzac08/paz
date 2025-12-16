from django import forms
from django.forms import inlineformset_factory
from .models import Idea, IdeaImage, TimeSlot, Service, RecurringSlotTemplate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, time, timedelta
import re
import json

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


class ServiceSelectForm(forms.Form):
    service = forms.ModelChoiceField(label='Usługa', queryset=None)

    def __init__(self, *args, **kwargs):
        qs = kwargs.pop('queryset', None)
        super().__init__(*args, **kwargs)
        if qs is None:
            from .models import Service
            qs = Service.objects.all()
        self.fields['service'].queryset = qs


class DateTimeSelectForm(forms.Form):
    date = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    time = forms.TimeField(
        label='Godzina',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )


class TermsAcceptanceForm(forms.Form):
    accept_terms = forms.BooleanField(
        label='Akceptuję regulamin i politykę prywatności',
        required=True,
        error_messages={'required': 'Musisz zaakceptować regulamin aby kontynuować'}
    )


class GuestBookingForm(forms.Form):
    """Formularz dla gości (bez konta)"""
    first_name = forms.CharField(
        label='Imię',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Imię'})
    )
    last_name = forms.CharField(
        label='Nazwisko',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwisko'})
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'adres@email.pl'})
    )
    phone = forms.CharField(
        label='Numer telefonu',
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+48 123 456 789'})
    )
    notes = forms.CharField(
        label='Uwagi (opcjonalnie)',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dodatkowe informacje...'})
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone = phone.strip()
            if not re.match(r'^\+?[0-9]{9,15}$', phone.replace(' ', '')):
                raise forms.ValidationError('Wprowadź prawidłowy numer telefonu (9-15 cyfr)')
        return phone


class RegisterAndBookForm(PolishUserCreationForm):
    """Formularz rejestracji podczas rezerwacji"""
    first_name = forms.CharField(
        label='Imię',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label='Nazwisko',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label='Numer telefonu',
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class ReservationConfirmForm(forms.Form):
    accept_terms = forms.BooleanField(label='Akceptuję regulamin')

    def clean_accept_terms(self):
        v = self.cleaned_data.get('accept_terms')
        if not v:
            raise forms.ValidationError('Musisz zaakceptować regulamin')
        return v


class CancellationForm(forms.Form):
    """Formularz odwoływania wizyty"""
    REASON_CHOICES = [
        ('change_plans', 'Zmiana planów'),
        ('illness', 'Choroba'),
        ('cannot_attend', 'Nie mogę się stawić'),
        ('other', 'Inny powód'),
    ]
    
    reason = forms.ChoiceField(
        label='Powód odwołania',
        choices=REASON_CHOICES,
        required=True,
        widget=forms.RadioSelect,
        error_messages={
            'required': 'Wybierz powód odwołania.',
        }
    )
    
    note = forms.CharField(
        label='Dodatkowe informacje (opcjonalnie)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Możesz dodać dodatkowe informacje...'
        })
    )


# ===== Time Slot Management Forms =====

class SingleTimeSlotForm(forms.ModelForm):
    """Formularz tworzenia pojedynczego slotu"""
    
    date = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat()
        }),
        error_messages={
            'required': 'Wybierz datę.',
            'invalid': 'Wprowadź prawidłową datę.'
        }
    )
    
    time = forms.TimeField(
        label='Godzina rozpoczęcia',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
            'step': '900'  # 15 minutes
        }),
        error_messages={
            'required': 'Wybierz godzinę.',
            'invalid': 'Wprowadź prawidłową godzinę.'
        }
    )
    
    class Meta:
        model = TimeSlot
        fields = ['service', 'status']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'service': 'Usługa (opcjonalnie dla blokad)',
            'status': 'Status',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].required = False
        self.fields['service'].help_text = 'Pozostaw puste dla globalnej blokady (wszystkie usługi)'
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time_value = cleaned_data.get('time')
        service = cleaned_data.get('service')
        status = cleaned_data.get('status')
        
        if not date or not time_value:
            return cleaned_data
        
        # Połącz datę i czas
        start_dt = timezone.make_aware(datetime.combine(date, time_value))
        
        # Sprawdź czy nie jest w przeszłości
        if start_dt < timezone.now():
            raise forms.ValidationError('Nie możesz utworzyć slotu w przeszłości.')
        
        # Dla dostępnych slotów wymagaj usługi
        if status == 'available' and not service:
            raise forms.ValidationError('Dostępny slot musi mieć przypisaną usługę.')
        
        # Oblicz end_dt
        if service:
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)
            
            # Sprawdź nakładanie tylko jeśli jest usługa
            conflicts = TimeSlot.objects.filter(
                service=service,
                start__lt=end_dt,
                end__gt=start_dt
            )
            
            if self.instance.pk:
                conflicts = conflicts.exclude(pk=self.instance.pk)
            
            if conflicts.exists():
                raise forms.ValidationError(
                    f'Istnieją już sloty w tym czasie: {", ".join([str(s.start.time()) for s in conflicts])}'
                )
        else:
            # Dla blokad bez usługi - domyślnie 1 godzina
            end_dt = start_dt + timedelta(hours=1)
        
        # Zapisz połączone wartości
        cleaned_data['start'] = start_dt
        cleaned_data['end'] = end_dt
        
        return cleaned_data


class RecurringTimeSlotForm(forms.Form):
    """Formularz tworzenia cyklicznych slotów"""
    
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        label='Usługa',
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={'required': 'Wybierz usługę.'}
    )
    
    start_date = forms.DateField(
        label='Data rozpoczęcia',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat()
        }),
        error_messages={'required': 'Wybierz datę rozpoczęcia.'}
    )
    
    end_date = forms.DateField(
        label='Data zakończenia',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        error_messages={'required': 'Wybierz datę zakończenia.'}
    )
    
    # Dni tygodnia
    monday = forms.BooleanField(label='Poniedziałek', required=False)
    tuesday = forms.BooleanField(label='Wtorek', required=False)
    wednesday = forms.BooleanField(label='Środa', required=False)
    thursday = forms.BooleanField(label='Czwartek', required=False)
    friday = forms.BooleanField(label='Piątek', required=False)
    saturday = forms.BooleanField(label='Sobota', required=False)
    sunday = forms.BooleanField(label='Niedziela', required=False)
    
    start_time = forms.TimeField(
        label='Godzina rozpoczęcia',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(9, 0),
        error_messages={'required': 'Wybierz godzinę rozpoczęcia.'}
    )
    
    end_time = forms.TimeField(
        label='Godzina zakończenia',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        initial=time(17, 0),
        error_messages={'required': 'Wybierz godzinę zakończenia.'}
    )
    
    slot_interval_minutes = forms.IntegerField(
        label='Interwał między slotami (minuty)',
        min_value=15,
        max_value=240,
        initial=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '15'
        }),
        required=False,
        help_text='Domyślnie: czas trwania usługi'
    )
    
    breaks = forms.CharField(
        label='Przerwy (opcjonalnie)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Format JSON: [{"start": "12:00", "end": "13:00", "name": "Przerwa obiadowa"}]'
        }),
        help_text='Lista przerw w formacie JSON'
    )
    
    save_as_template = forms.BooleanField(
        label='Zapisz jako szablon',
        required=False,
        initial=False
    )
    
    template_name = forms.CharField(
        label='Nazwa szablonu',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Np. "Standardowy tydzień roboczy"'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Walidacja dat
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.')
            
            if start_date < timezone.now().date():
                raise forms.ValidationError('Data rozpoczęcia nie może być w przeszłości.')
        
        # Walidacja czasów
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia.')
        
        # Sprawdź czy wybrano przynajmniej jeden dzień
        days = [
            cleaned_data.get('monday'),
            cleaned_data.get('tuesday'),
            cleaned_data.get('wednesday'),
            cleaned_data.get('thursday'),
            cleaned_data.get('friday'),
            cleaned_data.get('saturday'),
            cleaned_data.get('sunday'),
        ]
        
        if not any(days):
            raise forms.ValidationError('Wybierz przynajmniej jeden dzień tygodnia.')
        
        # Walidacja breaks JSON
        breaks_str = cleaned_data.get('breaks')
        if breaks_str:
            try:
                breaks_list = json.loads(breaks_str)
                if not isinstance(breaks_list, list):
                    raise forms.ValidationError('Przerwy muszą być listą.')
                cleaned_data['breaks_parsed'] = breaks_list
            except json.JSONDecodeError:
                raise forms.ValidationError('Nieprawidłowy format JSON dla przerw.')
        else:
            cleaned_data['breaks_parsed'] = []
        
        # Sprawdź wymóg nazwy szablonu
        if cleaned_data.get('save_as_template') and not cleaned_data.get('template_name'):
            raise forms.ValidationError('Podaj nazwę szablonu.')
        
        return cleaned_data


class CopyTimeSlotsForm(forms.Form):
    """Formularz kopiowania slotów"""
    
    source_start_date = forms.DateField(
        label='Data rozpoczęcia źródłowego okresu',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        error_messages={'required': 'Wybierz datę rozpoczęcia źródłowego okresu.'}
    )
    
    source_end_date = forms.DateField(
        label='Data zakończenia źródłowego okresu',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        error_messages={'required': 'Wybierz datę zakończenia źródłowego okresu.'}
    )
    
    target_start_date = forms.DateField(
        label='Data rozpoczęcia docelowego okresu',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat()
        }),
        error_messages={'required': 'Wybierz datę rozpoczęcia docelowego okresu.'}
    )
    
    copy_blocked = forms.BooleanField(
        label='Kopiuj również zablokowane sloty',
        required=False,
        initial=False
    )
    
    skip_existing = forms.BooleanField(
        label='Pomiń istniejące sloty (nie nadpisuj)',
        required=False,
        initial=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        source_start = cleaned_data.get('source_start_date')
        source_end = cleaned_data.get('source_end_date')
        target_start = cleaned_data.get('target_start_date')
        
        if source_start and source_end:
            if source_end < source_start:
                raise forms.ValidationError('Data zakończenia źródłowego okresu nie może być wcześniejsza niż data rozpoczęcia.')
        
        if target_start and target_start < timezone.now().date():
            raise forms.ValidationError('Data rozpoczęcia docelowego okresu nie może być w przeszłości.')
        
        return cleaned_data


class BlockTimeSlotsForm(forms.Form):
    """Formularz blokowania slotów"""
    
    start_date = forms.DateField(
        label='Data rozpoczęcia',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': timezone.now().date().isoformat()
        }),
        error_messages={'required': 'Wybierz datę rozpoczęcia.'}
    )
    
    end_date = forms.DateField(
        label='Data zakończenia',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        error_messages={'required': 'Wybierz datę zakończenia.'}
    )
    
    start_time = forms.TimeField(
        label='Godzina rozpoczęcia (opcjonalnie)',
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        help_text='Pozostaw puste aby zablokować cały dzień'
    )
    
    end_time = forms.TimeField(
        label='Godzina zakończenia (opcjonalnie)',
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        }),
        help_text='Pozostaw puste aby zablokować cały dzień'
    )
    
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        label='Usługi (opcjonalnie)',
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Pozostaw puste aby utworzyć globalną blokadę dla wszystkich usług (np. urlop, zamknięcie salonu)'
    )
    
    block_reason = forms.ChoiceField(
        label='Powód blokady',
        choices=TimeSlot.BLOCK_REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={'required': 'Wybierz powód blokady.'}
    )
    
    block_note = forms.CharField(
        label='Notatka',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Dodatkowe informacje o blokadzie...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.')
            
            if start_date < timezone.now().date():
                raise forms.ValidationError('Data rozpoczęcia nie może być w przeszłości.')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia.')
        
        if (start_time and not end_time) or (end_time and not start_time):
            raise forms.ValidationError('Podaj obie godziny lub zostaw obie puste.')
        
        return cleaned_data
