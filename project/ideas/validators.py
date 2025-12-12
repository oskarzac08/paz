"""
Polskie walidatory haseł
"""
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    CommonPasswordValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator
)


class PolishMinimumLengthValidator(MinimumLengthValidator):
    """Walidator minimalnej długości hasła z polskimi komunikatami"""
    
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f'Hasło musi zawierać co najmniej {self.min_length} znaków.',
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self):
        return f'Hasło musi zawierać co najmniej {self.min_length} znaków.'


class PolishCommonPasswordValidator(CommonPasswordValidator):
    """Walidator popularnych haseł z polskimi komunikatami"""
    
    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError(
                'Hasło jest zbyt popularne.',
                code='password_too_common',
            )

    def get_help_text(self):
        return 'Hasło nie może być powszechnie używanym hasłem.'


class PolishNumericPasswordValidator(NumericPasswordValidator):
    """Walidator numerycznego hasła z polskimi komunikatami"""
    
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                'Hasło nie może składać się wyłącznie z cyfr.',
                code='password_entirely_numeric',
            )

    def get_help_text(self):
        return 'Hasło nie może składać się wyłącznie z cyfr.'


class PolishUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    """Walidator podobieństwa do danych użytkownika z polskimi komunikatami"""
    
    def __init__(self, user_attributes=('username', 'first_name', 'last_name', 'email'), max_similarity=0.7):
        self.user_attributes = user_attributes
        self.max_similarity = max_similarity

    def validate(self, password, user=None):
        if not user:
            return

        password = password.lower()
        for attribute_name in self.user_attributes:
            value = getattr(user, attribute_name, None)
            if not value or not isinstance(value, str):
                continue
            value_lower = value.lower()
            
            # Sprawdź czy hasło zawiera wartość atrybutu
            if value_lower in password or password in value_lower:
                raise ValidationError(
                    'Hasło jest zbyt podobne do innych danych osobowych.',
                    code='password_too_similar',
                )
            
            # Sprawdź podobieństwo używając SequenceMatcher
            from difflib import SequenceMatcher
            if SequenceMatcher(a=password, b=value_lower).quick_ratio() >= self.max_similarity:
                raise ValidationError(
                    'Hasło jest zbyt podobne do innych danych osobowych.',
                    code='password_too_similar',
                )

    def get_help_text(self):
        return 'Hasło nie może być zbyt podobne do innych danych osobowych.'
