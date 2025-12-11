# PDR-001: Dwukanałowa weryfikacja użytkowników

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

System rezerwacji wizyt wymaga pewności, że użytkownicy podający swoje dane kontaktowe rzeczywiście mają do nich dostęp. Niepotwierdzone dane kontaktowe prowadzą do:

- Niemożności skontaktowania się z klientem przed wizytą
- Nieodebranych przypomnień o wizytach
- Pustych slotów przez no-show
- Frustracji obsługi przy próbach kontaktu
- Potencjalnych rezerwacji spamowych

### Potrzeby użytkowników

**Klient:**

- Chce łatwo i szybko zarejestrować się
- Nie chce tracić czasu na skomplikowane procedury
- Oczekuje potwierdzenia, że jego rezerwacja została przyjęta
- Chce otrzymywać powiadomienia na preferowany kanał

**Obsługa:**

- Potrzebuje pewności, że dane kontaktowe są aktualne
- Chce móc skontaktować się z klientem w razie potrzeby
- Oczekuje redukcji no-show przez weryfikację
- Chce mieć pewność, że powiadomienia dotrą do klienta

## Decyzja

Implementujemy **dwukanałowy system weryfikacji** z następującymi założeniami:

### 1. Weryfikacja e-mail

**Metoda:** 6-cyfrowy kod wysyłany na adres e-mail

**Flow:**

1. Użytkownik podaje adres e-mail podczas rejestracji
2. System wysyła kod weryfikacyjny na e-mail (np. "123456")
3. Użytkownik wprowadza kod w formularzu
4. Po poprawnym wprowadzeniu, e-mail jest oznaczony jako zweryfikowany

**Ważność:** 24 godziny

### 2. Weryfikacja SMS

**Metoda:** 6-cyfrowy kod wysyłany SMS-em

**Flow:**

1. Użytkownik podaje numer telefonu podczas rejestracji
2. System wysyła kod SMS
3. Użytkownik wprowadza kod
4. Po poprawnym wprowadzeniu, numer jest zweryfikowany

**Ważność:** 24 godziny

### 3. Wybór preferowanego kanału

Użytkownik podczas rejestracji wybiera, którym kanałem preferuje otrzymywać:

- Powiadomienia o rezerwacjach
- Przypomnienia o wizytach
- Informacje o zmianach

**Domyślnie:** E-mail (niższy koszt)

### 4. Wymagania weryfikacji

- **Minimum jeden kanał musi być zweryfikowany** aby dokonać rezerwacji
- Użytkownik może zweryfikować oba kanały (zalecane)
- Niezweryfikowane konto ma ograniczony dostęp (tylko przeglądanie)
- Po 7 dniach bez weryfikacji konto jest automatycznie usuwane

## Uzasadnienie

### Dlaczego kod zamiast linku?

**E-mail:**

- Kod jest prostszy do wpisania na mobile
- Nie wymaga otwierania przeglądarki
- Mniej podatny na filtry spam (krótka wiadomość)
- Łatwiejszy do przekopiowania między urządzeniami

**SMS:**

- SMS z linkiem może być oznaczony jako spam
- Kod jest standardem dla SMS (np. bankowość)
- Krótszy SMS = niższy koszt

### Dlaczego 6 cyfr?

- **Bezpieczeństwo:** 1,000,000 kombinacji
- **Użyteczność:** Łatwy do zapamiętania i wpisania
- **Standard:** Używany przez Google, Facebook, banki
- **Mobile-friendly:** Często auto-wypełniany przez iOS/Android

### Dlaczego 24h ważności?

- **Wygoda:** Użytkownik może wrócić następnego dnia
- **Bezpieczeństwo:** Nie za długo, by minimalizować ryzyko
- **Praktyczność:** Uwzględnia strefy czasowe, przerwę na noc

### Dlaczego wymóg minimum jednego kanału?

- **Kompromis:** Nie zmuszamy do obu (może nie mieć telefonu/e-maila)
- **Elastyczność:** Użytkownik wybiera co mu wygodniej
- **Efektywność:** Przynajmniej jeden działający kanał komunikacji

## User Stories

### US-001: Rejestracja z weryfikacją e-mail

```
Jako nowy użytkownik
Chcę zarejestrować się podając e-mail
Aby otrzymać kod weryfikacyjny i potwierdzić konto
```

**Acceptance Criteria:**

- Formularz rejestracji zawiera pole e-mail
- Po submit otrzymuję kod na e-mail w max 2 minuty
- Mogę wprowadzić kod w formularzu
- Po poprawnym kodzie widzę komunikat "E-mail zweryfikowany"
- Mogę poprosić o ponowne wysłanie kodu (max 3x/godzinę)

### US-002: Wybór preferowanego kanału

```
Jako użytkownik
Chcę wybrać preferowany kanał komunikacji (e-mail lub SMS)
Aby otrzymywać powiadomienia wygodnym dla mnie sposobem
```

**Acceptance Criteria:**

- Podczas rejestracji widzę opcję wyboru kanału
- Mogę wybrać: E-mail, SMS lub Oba
- Wybór jest zapisywany w profilu
- Mogę zmienić wybór później w ustawieniach

### US-003: Rejestracja przez obsługę

```
Jako pracownik obsługi
Chcę zarejestrować klienta telefonicznie
Aby móc utworzyć mu rezerwację bez jego udziału
```

**Acceptance Criteria:**

- Formularz dla obsługi pozwala na wprowadzenie danych klienta
- System automatycznie wysyła kod weryfikacyjny
- Obsługa może oznaczyć konto jako "zweryfikowane przez obsługę"
- Klient otrzymuje powiadomienie o utworzeniu konta

## UX/UI Guidelines

### Formularz rejestracji

```
┌─────────────────────────────────────┐
│  Rejestracja                        │
├─────────────────────────────────────┤
│                                     │
│  Imię: [____________]               │
│  Nazwisko: [____________]           │
│                                     │
│  E-mail: [____________]             │
│  Telefon: [+48 _________]           │
│                                     │
│  Preferowany kontakt:               │
│  ○ E-mail  ○ SMS  ○ Oba            │
│                                     │
│  [ ] Akceptuję regulamin           │
│                                     │
│  [   Zarejestruj się   ]           │
└─────────────────────────────────────┘
```

### Ekran weryfikacji

```
┌─────────────────────────────────────┐
│  Weryfikacja konta                  │
├─────────────────────────────────────┤
│                                     │
│  Wysłaliśmy kod na:                 │
│  ✉ user@example.com                │
│                                     │
│  Wprowadź 6-cyfrowy kod:            │
│  [___] [___] [___] [___] [___] [___]│
│                                     │
│  ⏱ Kod ważny przez: 23:45          │
│                                     │
│  [     Potwierdź     ]             │
│                                     │
│  Nie otrzymałeś kodu?              │
│  Wyślij ponownie (dostępne za 2:00)│
│                                     │
└─────────────────────────────────────┘
```

### Komunikaty

**Sukces:**

- ✅ "Kod wysłany! Sprawdź swoją skrzynkę e-mail"
- ✅ "E-mail zweryfikowany pomyślnie"
- ✅ "Możesz teraz dokonywać rezerwacji"

**Błędy:**

- ❌ "Nieprawidłowy kod. Pozostały próby: 2"
- ❌ "Kod wygasł. Wyślij nowy kod."
- ⚠️ "Limit wysyłek osiągnięty. Spróbuj za 1 godzinę"

### Dostępność

- Auto-focus na pierwszym polu kodu
- Auto-submit po wpisaniu 6 cyfr
- Obsługa paste (wklej cały kod)
- Licznik czasu do wygaśnięcia
- Czytnik ekranu: "Pole 1 z 6"

## Metryki sukcesu

### KPI

- **Conversion rate:** >80% użytkowników kończy weryfikację
- **Time to verify:** <3 minuty średnio
- **Delivery rate:** >95% kodów dostarczonych
- **No-show reduction:** -30% po wprowadzeniu weryfikacji

### Monitoring

- Liczba wysłanych kodów (e-mail/SMS)
- Liczba błędnych prób weryfikacji
- Czas od rejestracji do weryfikacji
- % użytkowników weryfikujących oba kanały
- Koszty SMS

## Konsekwencje

### Pozytywne dla użytkownika

- ✅ Pewność, że powiadomienia dotrą
- ✅ Wybór preferowanego kanału
- ✅ Szybki proces (kod zamiast linku)
- ✅ Możliwość zmiany kanału później

### Pozytywne dla biznesu

- ✅ Mniej no-show przez lepszą komunikację
- ✅ Zweryfikowane dane kontaktowe
- ✅ Redukcja spam/fake accounts
- ✅ Compliance z wymogami prawnymi (RODO)

### Negatywne

- ⚠️ Dodatkowy krok w rejestracji (friction)
- ⚠️ Koszty SMS (0.10-0.20 PLN/SMS)
- ⚠️ Możliwe problemy z dostarczalnością (spam filters)
- ⚠️ Użytkownicy bez dostępu do e-mail/telefonu

### Mitigacje

**Friction:** Proces max 2 minuty, auto-submit, komunikaty pomocne

**Koszty SMS:** Domyślnie e-mail, SMS tylko na życzenie

**Dostarczalność:** Monitoring, whitelisting IP, sender reputation

**Dostępność:** Alternatywna weryfikacja przez obsługę

## Alternatywy rozważone

### 1. Link weryfikacyjny w e-mail

**Odrzucone:**

- Wymaga otwarcia przeglądarki
- Problemy z mobile deep linking
- Łatwiej trafia do spam

### 2. Weryfikacja tylko jednego kanału

**Odrzucone:**

- Ogranicza elastyczność komunikacji
- Część użytkowników nie ma e-mail/telefonu
- Nie pozwala na wybór preferencji

### 3. Brak weryfikacji

**Odrzucone:**

- Wysokie ryzyko fake accounts
- Niemożność dotarcia z powiadomieniami
- Więcej no-show

### 4. Captcha zamiast weryfikacji

**Odrzucone:**

- Nie weryfikuje danych kontaktowych
- Tylko anti-bot, nie weryfikacja tożsamości

## Implementacja

### Faza 1: MVP (Miesiąc 1)

- Weryfikacja e-mail z kodem
- Podstawowy formularz rejestracji
- Wybór preferowanego kanału

### Faza 2: Rozszerzenie (Miesiąc 2)

- Weryfikacja SMS
- Rate limiting
- Dashboard dla obsługi (weryfikacja manualna)

### Faza 3: Optymalizacja (Miesiąc 3)

- Auto-fill kodu z SMS (iOS/Android)
- Monitoring delivery rate
- A/B testing różnych długości kodów

## Odniesienia

- RODO - wymogi przetwarzania danych kontaktowych
- Best practices: Google 2FA, Banking OTP systems
- User research: 87% użytkowników preferuje kod vs link (internal survey)
- Cost analysis: E-mail €0.001, SMS €0.04 per message
