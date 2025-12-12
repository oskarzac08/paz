# Weryfikacja dwukanałowa - Instrukcja testowania

## Uruchomienie aplikacji

### 1. Uruchom serwer deweloperski
```powershell
cd d:\start\project
uv run python manage.py runserver
```

Serwer będzie dostępny pod adresem: http://127.0.0.1:8000/

### 2. Otwórz przeglądarkę
Przejdź do: http://127.0.0.1:8000/

## Testowanie funkcjonalności

### Scenariusz 1: Rejestracja z weryfikacją e-mail

1. **Kliknij "Zarejestruj się"** lub przejdź do http://127.0.0.1:8000/register/

2. **Wypełnij formularz:**
   - Nazwa użytkownika: `testuser1`
   - E-mail: `test1@example.com`
   - Numer telefonu: *(zostaw puste lub wpisz +48123456789)*
   - Preferowany kanał: **E-mail**
   - Hasło: `TestPass123!`
   - Powtórz hasło: `TestPass123!`

3. **Kliknij "Zarejestruj się"**

4. **Sprawdź terminal/konsolę** - kod weryfikacyjny zostanie wyświetlony:
   ```
   Content-Type: text/plain; charset="utf-8"
   From: noreply@example.com
   To: test1@example.com
   Subject: Kod weryfikacyjny
   
   Twój kod weryfikacyjny to: 123456
   ```

5. **Wprowadź kod** na stronie weryfikacji (6 cyfr)

6. **Po pomyślnej weryfikacji** zostaniesz automatycznie zalogowany i przekierowany do `/ideas/`

### Scenariusz 2: Rejestracja z weryfikacją SMS

1. **Przejdź do rejestracji** http://127.0.0.1:8000/register/

2. **Wypełnij formularz:**
   - Nazwa użytkownika: `testuser2`
   - E-mail: `test2@example.com`
   - Numer telefonu: **+48987654321** *(wymagane dla SMS)*
   - Preferowany kanał: **SMS**
   - Hasło: `TestPass123!`
   - Powtórz hasło: `TestPass123!`

3. **Kliknij "Zarejestruj się"**

4. **Sprawdź terminal** - kod SMS zostanie wylogowany:
   ```
   INFO ... ideas.services SMS verification code to +48987654321: 654321
   ```

5. **Wprowadź kod SMS**

6. **Zostaniesz zalogowany** po weryfikacji

### Scenariusz 3: Weryfikacja oboma kanałami

1. **Zarejestruj się** z opcją **"Oba"**
2. **Podaj e-mail i telefon**
3. **Otrzymasz kody** na oba kanały
4. **Użyj dowolnego kodu** do weryfikacji
5. **Konto zostanie aktywowane** po jednej poprawnej weryfikacji

### Scenariusz 4: Ponowne wysłanie kodu

1. **Podczas weryfikacji** kliknij "Wyślij ponownie"
2. **Wybierz kanał** (Email lub SMS)
3. **Nowy kod** zostanie wygenerowany (poprzedni unieważniony)
4. **Sprawdź terminal** dla nowego kodu
5. **Wprowadź nowy kod**

### Scenariusz 5: Błędny kod

1. **Wprowadź nieprawidłowy kod** np. `000000`
2. **Zobaczysz komunikat błędu:** "Nieprawidłowy lub wygasły kod weryfikacyjny"
3. **Spróbuj ponownie** z właściwym kodem

### Scenariusz 6: Rate limiting

1. **Wyślij kod ponownie** 3 razy w ciągu godziny
2. **Przy 4. próbie** zobaczysz komunikat: "Przekroczono limit wysłanych kodów. Spróbuj ponownie za godzinę."

### Scenariusz 7: Status weryfikacji

1. **Zaloguj się** na konto
2. **Przejdź do** http://127.0.0.1:8000/verification-status/
3. **Sprawdź status** weryfikacji e-mail i telefonu
4. **Dla niezweryfikowanych** kanałów - kliknij "Wyślij kod weryfikacyjny"

## Panel administracyjny

### Dostęp do panelu

1. **Utwórz superusera** (jeśli jeszcze nie istnieje):
   ```powershell
   cd d:\start\project
   uv run python manage.py createsuperuser
   ```
   
2. **Zaloguj się** do panelu: http://127.0.0.1:8000/admin/
   - Username: admin
   - Password: (twoje hasło)

### Co sprawdzić w panelu

#### Użytkownicy (Users)
1. **Kliknij Users** w panelu
2. **Kolumny dodatkowe:**
   - Data aktywacji
   - E-mail zweryfikowany (✓/✗)
   - Telefon zweryfikowany (✓/✗)

3. **Kliknij na użytkownika** - zobaczysz:
   - Sekcja "Profil użytkownika"
   - Numer telefonu
   - Preferowany kanał kontaktu
   - Status weryfikacji obu kanałów

#### Kody aktywacyjne (Activation codes)
1. **Kliknij Activation codes**
2. **Zobacz listę wszystkich kodów:**
   - User
   - 6-cyfrowy kod
   - Kanał (email/sms)
   - Data utworzenia
   - Data wygaśnięcia
   - Czy użyty
   - Czy ważny

3. **Filtry:**
   - Kanał (email/sms)
   - Czy użyty
   - Data utworzenia

4. **Wyszukiwanie:**
   - Po username
   - Po email
   - Po kodzie

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'django'"
**Rozwiązanie:** Uruchom polecenia przez `uv run`:
```powershell
uv run python manage.py runserver
```

### Problem: Nie widzę kodu w konsoli
**Rozwiązanie:** 
1. Sprawdź czy EMAIL_BACKEND w settings.py to:
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
   ```
2. Kody powinny pojawiać się bezpośrednio w terminalu gdzie działa `runserver`

### Problem: Formularz wymaga numeru telefonu mimo wyboru "E-mail"
**Rozwiązanie:** To poprawne - telefon jest opcjonalny dla "E-mail", ale wymagany dla "SMS" i "Oba"

### Problem: "Link jest nieważny lub nie istnieje" przy starym URLu aktywacji
**Rozwiązanie:** Stary system aktywacji przez link został zastąpiony kodami. Użyj nowego flow rejestracji.

### Problem: Kod wygasł
**Rozwiązanie:** Kody ważne są 24h. Jeśli wygasł:
1. Kliknij "Wyślij ponownie"
2. Otrzymasz nowy kod

## Kody testowe w development

W trybie development (console backend):
- **E-mail:** Kod pojawi się w output terminala jako treść wiadomości
- **SMS:** Kod pojawi się w logach: `INFO ... SMS verification code to +48XXX: 123456`

## Przykładowe dane testowe

```
User 1:
- Username: alice
- Email: alice@example.com
- Phone: +48111222333
- Preferred: email

User 2:
- Username: bob
- Email: bob@example.com
- Phone: +48444555666
- Preferred: sms

User 3:
- Username: charlie
- Email: charlie@example.com
- Phone: +48777888999
- Preferred: both
```

## Sprawdzenie bazy danych

```powershell
cd d:\start\project
uv run python manage.py dbshell
```

Zapytania SQL:
```sql
-- Wszyscy użytkownicy z profilem
SELECT u.username, u.email, u.is_active, p.email_verified, p.phone_verified 
FROM auth_user u 
LEFT JOIN ideas_userprofile p ON u.id = p.user_id;

-- Wszystkie kody weryfikacyjne
SELECT u.username, ac.code, ac.channel, ac.created_at, ac.is_used 
FROM ideas_activationcode ac 
JOIN auth_user u ON ac.user_id = u.id 
ORDER BY ac.created_at DESC 
LIMIT 10;

-- Statystyki weryfikacji
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN p.email_verified THEN 1 ELSE 0 END) as email_verified,
    SUM(CASE WHEN p.phone_verified THEN 1 ELSE 0 END) as phone_verified
FROM auth_user u
LEFT JOIN ideas_userprofile p ON u.id = p.user_id;
```

## Następne kroki po testach

1. **Jeśli wszystko działa:**
   - Przejdź do konfiguracji prawdziwego backendu e-mail (SMTP)
   - Skonfiguruj bramkę SMS (Twilio)
   - Dodaj Celery dla asynchronicznej wysyłki
   - Dodaj testy automatyczne

2. **Jeśli są problemy:**
   - Sprawdź logi w terminalu
   - Sprawdź bazę danych
   - Zobacz `docs/IMPLEMENTATION.md` dla szczegółów
   - Przejrzyj `docs/pdr/001-dwukanalowa-weryfikacja.md`

## Dokumentacja

- **PDR-001:** `/docs/pdr/001-dwukanalowa-weryfikacja.md` - Wymagania produktowe
- **ADR-003:** `/docs/adr/003-weryfikacja-uzytkownika.md` - Decyzje architektoniczne  
- **IMPLEMENTATION:** `/docs/IMPLEMENTATION.md` - Szczegóły implementacji

---

**Status implementacji:** ✅ Gotowe do testów
**Branch:** weryfikacja
**Wersja:** 1.0.0
