# ADR-001: Wybór Django jako frameworka głównego

## Status
Zaakceptowany

## Kontekst

Projekt wymaga budowy systemu rezerwacji wizyt z następującymi wymaganiami:
- Zarządzanie użytkownikami (klienci i obsługa)
- System rezerwacji terminów
- Zarządzanie usługami
- Weryfikacja użytkowników (SMS i e-mail)
- Panel administracyjny dla obsługi
- Interfejs użytkownika dla klientów

Potrzebujemy frameworka webowego, który:
- Oferuje wbudowany system ORM do zarządzania bazą danych
- Posiada gotowy system autentykacji i autoryzacji
- Zapewnia bezpieczeństwo (CSRF, SQL injection, XSS)
- Ma aktywną społeczność i dokumentację
- Pozwala na szybki rozwój aplikacji
- Jest skalowalny

## Decyzja

Wybieramy **Django** (wersja 5.2.8) jako główny framework aplikacji webowej.

## Uzasadnienie

### Django oferuje:
1. **Batteries-included philosophy** - wbudowane komponenty:
   - System ORM (Object-Relational Mapping)
   - System autentykacji użytkowników
   - Panel administracyjny
   - System formularzy z walidacją
   - Middleware dla bezpieczeństwa
   - System migracji bazy danych

2. **Bezpieczeństwo**:
   - Ochrona przed CSRF, SQL injection, XSS
   - Bezpieczne zarządzanie sesjami
   - Hashowanie haseł z bcrypt/PBKDF2

3. **ORM Django**:
   - Abstrakcja nad bazą danych
   - Łatwe tworzenie i modyfikacja modeli
   - System migracji
   - Wsparcie dla relacji (ForeignKey, ManyToMany)

4. **Ekosystem**:
   - Bogaty ekosystem pakietów (django-rest-framework, celery, channels)
   - Dobra dokumentacja
   - Duża społeczność

5. **Rozwój w Pythonie**:
   - Czytelny kod
   - Łatwa integracja z bibliotekami Python (np. do wysyłania SMS, e-mail)

## Konsekwencje

### Pozytywne:
- Szybki rozwój dzięki gotowym komponentom
- Bezpieczeństwo out-of-the-box
- Łatwa obsługa bazy danych przez ORM
- Gotowy panel administracyjny
- Silna typizacja modeli danych
- Łatwe testowanie

### Negatywne:
- Monolityczna architektura (trudniejsza mikrousługowa architektura)
- Większe zużycie zasobów niż w micro-frameworkach (Flask)
- Krzywa uczenia się dla pełnego wykorzystania możliwości
- Może być over-engineering dla bardzo prostych aplikacji

## Alternatywy rozważone

1. **Flask** - Odrzucony ze względu na brak wbudowanych komponentów (auth, admin, ORM)
2. **FastAPI** - Odrzucony ze względu na koncentrację na API, brak panelu admin
3. **Ruby on Rails** - Odrzucony ze względu na wybór Pythona jako języka głównego

## Implementacja

Struktura projektu Django:
```
project/
├── manage.py
├── project/          # Konfiguracja główna
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── ideas/           # Aplikacja (zostanie rozbudowana o moduły rezerwacji)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── migrations/
```

## Odniesienia
- Django Documentation: https://docs.djangoproject.com/
- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
