# PDR-004: System odwoływania wizyt

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Odwoływanie wizyt to krytyczna funkcjonalność wpływająca na:

- **Wykorzystanie zasobów:** Puste sloty = strata przychodów
- **Satysfakcję klientów:** Łatwość odwołania = lepsza UX
- **Planowanie:** Wcześniejsze odwołanie = możliwość zapełnienia slotu

Obecna sytuacja (rezerwacje bez systemu odwoływania):

- Klienci zapominają odwołać → no-show
- Późne odwołania (10 min przed) → brak czasu na zapełnienie
- Niejasne zasady odwoływania → konflikty
- Brak historii odwołań → trudność w identyfikacji problematycznych klientów

### Potrzeby użytkowników

**Klient:**

- Łatwe odwołanie online (bez dzwonienia)
- Jasne zasady (do kiedy można odwołać)
- Potwierdzenie odwołania
- Możliwość odwołania z linku w e-mailu

**Obsługa:**

- Natychmiastowe zwolnienie slotu
- Powiadomienie o odwołaniu przez klienta
- Historia odwołań klienta
- Możliwość odwołania w imieniu klienta

**Biznes:**

- Polityka odwoływania (np. 24h przed)
- Redukcja no-show
- Możliwość zapełnienia zwolnionych slotów
- Analityka przyczyn odwołań

## Decyzja

Implementujemy **dwutorowy system odwoływania** z następującymi zasadami:

### 1. Zasady odwoływania

**Minimalne okno odwołania:** 24 godziny przed wizytą

**Wyjątki:**

- Obsługa może odwołać wizytę w każdym momencie
- Klient może odwołać <24h z zaznaczeniem "Pilne odwołanie" (opcjonalne)
- W przypadkach losowych (choroba) - kontakt z obsługą

**Konsekwencje późnego odwołania:**

- Brak konsekwencji w MVP (warning only)
- Przyszłość: System punktowy / opłaty (Faza 2)

### 2. Odwoływanie przez klienta

**Flow online:**

1. Klient loguje się do systemu
2. Widzi listę swoich nadchodzących wizyt
3. Wybiera wizytę do odwołania
4. Kliknięcie "Odwołaj wizytę"
5. Modal z potwierdzeniem:

```text
┌─────────────────────────────────────┐
│  Odwołanie wizyty                   │
├─────────────────────────────────────┤
│  Czy na pewno odwołać wizytę?       │
│                                     │
│  Usługa: Strzyżenie damskie        │
│  Termin: 15.12.2025, 14:00         │
│                                     │
│  ⚠️ Do wizyty pozostało: 3 dni     │
│     Możesz odwołać bez konsekwencji│
│                                     │
│  Powód (opcjonalnie):              │
│  ▼ [Wybierz z listy]               │
│  □ Zmiana planów                   │
│  □ Choroba                         │
│  □ Nie mogę się stawić             │
│  □ Inny: [_______________]         │
│                                     │
│  [Anuluj]  [Potwierdź odwołanie]  │
└─────────────────────────────────────┘
```

6. Po potwierdzeniu:
   - Status wizyty → "Odwołana"
   - Slot → "Dostępny"
   - E-mail/SMS potwierdzenie
   - Powiadomienie do obsługi

**Odwołanie z linku w e-mailu:**

```text
Temat: Przypomnienie o wizycie - 15.12.2025

Witaj Jan,

Przypominamy o Twojej wizycie:
Usługa: Strzyżenie damskie
Data: 15 grudnia 2025, godz. 14:00

[Zobacz szczegóły] [Odwołaj wizytę]

Możesz odwołać wizytę do 14.12.2025, 14:00
(24 godziny przed terminem)
```

**Kliknięcie "Odwołaj wizytę":**

- Przekierowanie do strony odwołania (z tokenem w URL)
- Brak wymogu logowania (one-click cancellation)
- Formularz z potwierdzeniem (jak wyżej)

**Zabezpieczenia:**

- Token w URL ważny 7 dni
- Token jednorazowy (po użyciu wygasa)
- Nie można odwołać już odwołanej wizyty

### 3. Odwoływanie przez obsługę

**Flow:**

1. Obsługa wyszukuje rezerwację (lub klienta dzwoni)
2. Widok szczegółów wizyty
3. Przycisk "Odwołaj wizytę"
4. Modal z dodatkowymi polami:

```text
┌─────────────────────────────────────┐
│  Odwołanie wizyty (obsługa)         │
├─────────────────────────────────────┤
│  Klient: Jan Kowalski               │
│  Usługa: Strzyżenie męskie          │
│  Termin: 15.12.2025, 10:00          │
│                                     │
│  Odwołane przez:                    │
│  ○ Klienta (telefon/wizyta)        │
│  ○ Salon (zaproponuj nowy termin)  │
│                                     │
│  Powód:                             │
│  [_____________________________]    │
│                                     │
│  □ Wyślij powiadomienie do klienta │
│  □ Zaproponuj alternatywne terminy │
│                                     │
│  [Anuluj]  [Potwierdź odwołanie]  │
└─────────────────────────────────────┘
```

5. Opcje po odwołaniu:
   - Natychmiastowa rezerwacja nowego terminu
   - Dodanie klienta do listy oczekujących
   - Notatka w profilu klienta

**Uprawnienia:**

- Obsługa może odwołać dowolną wizytę
- Brak ograniczeń czasowych (24h)
- Log: kto, kiedy, dlaczego

### 4. Powiadomienia o odwołaniu

**Do klienta (e-mail/SMS):**

```text
Twoja wizyta została odwołana

Usługa: Strzyżenie damskie
Termin: 15.12.2025, 14:00

Wizyta została odwołana przez: Ciebie
Data odwołania: 12.12.2025, 18:30

Chcesz umówić nową wizytę?
[Zarezerwuj ponownie]

Zespół [Nazwa Salonu]
```

**Do obsługi (e-mail):**

```text
Temat: Klient odwołał wizytę - 15.12.2025

Jan Kowalski odwołał wizytę:

Usługa: Strzyżenie damskie
Termin: 15.12.2025, 14:00
Powód: Zmiana planów
Odwołano: 12.12.2025, 18:30

Slot jest teraz dostępny dla innych klientów.

[Zobacz w systemie]
```

**Dashboard obsługi - alert:**

```text
🔔 Nowe odwołania (3)
• 14:00 - Jan Kowalski (Strzyżenie damskie)
• 15:30 - Anna Nowak (Koloryzacja)
• 16:00 - Piotr Wiśniewski (Stylizacja)
```

### 5. Historia odwołań

**W profilu klienta:**

```text
Historia wizyt - Jan Kowalski

✓ 01.12.2025  Strzyżenie męskie  (Zrealizowana)
✗ 15.11.2025  Strzyżenie męskie  (Odwołana przez klienta, 2 dni przed)
✓ 01.11.2025  Strzyżenie męskie  (Zrealizowana)
✗ 20.10.2025  Stylizacja         (No-show)
✓ 01.10.2025  Strzyżenie męskie  (Zrealizowana)

Statystyki:
• Odwołania: 2/5 (40%)
• No-show: 1/5 (20%)
• Średnie odwołanie: 2 dni przed wizytą
```

**Flagowanie problematycznych klientów:**

- >50% odwołań → ⚠️ Ostrzeżenie
- >2 no-show → 🚫 Wymagana przedpłata (Faza 2)

### 6. Re-booking po odwołaniu

**Opcja dla klienta:**

Po odwołaniu wizyty, system pokazuje:

```text
┌─────────────────────────────────────┐
│  ✓ Wizyta odwołana                  │
├─────────────────────────────────────┤
│  Chcesz zarezerwować nowy termin?   │
│                                     │
│  Najbliższe dostępne terminy:       │
│  • Jutro, 16.12.2025, 10:00        │
│  • Pojutrze, 17.12.2025, 14:00     │
│  • 18.12.2025, 09:00               │
│                                     │
│  [Zobacz więcej terminów]          │
│                                     │
│  lub                                │
│                                     │
│  [Powiadom gdy pojawi się termin]  │
└─────────────────────────────────────┘
```

**Waiting list (lista oczekujących):**

- Klient może dodać się do listy oczekujących
- Kiedy slot się zwolni → automatyczne powiadomienie
- "Slot dostępny: 15.12.2025, 14:00. Zarezerwuj w ciągu 2h"
- FCFS (First Come First Served)

## Uzasadnienie

### Dlaczego 24h minimum?

- **Czas na zapełnienie:** Możliwość znalezienia nowego klienta
- **Planowanie:** Obsługa może przygotować grafik
- **Standard branżowy:** Większość salonów ma podobną politykę
- **Redukcja no-show:** Wymusza planowanie z wyprzedzeniem

### Dlaczego zbierać powód odwołania?

- **Analityka:** Zrozumienie przyczyn (może zmiana oferty?)
- **Segmentacja:** "Choroba" vs "Znalazłem tańszy salon"
- **Optymalizacja:** Redukcja przyczyn odwołań
- **Relacje:** Możliwość kontaktu follow-up

### Dlaczego one-click z e-maila?

- **Wygoda:** Najszybsza metoda dla klienta
- **Mobile-friendly:** Działa na każdym urządzeniu
- **Conversion:** Więcej odwołań = mniej no-show
- **Standard:** Używany przez Booking.com, Uber, itp.

### Dlaczego powiadomienie do obsługi?

- **Proaktywność:** Możliwość szybkiego zapełnienia slotu
- **Komunikacja:** Telefoniczny follow-up jeśli potrzebny
- **Marketing:** Możliwość oferty dla klienta z listy oczekujących

## User Stories

### US-001: Odwołanie przez klienta online

```gherkin
Jako klient
Chcę odwołać moją wizytę online
Aby nie dzwonić do salonu

Acceptance Criteria:
- Widzę listę moich wizyt w profilu
- Mogę odwołać wizytę >24h przed terminem
- Otrzymuję potwierdzenie e-mailem/SMS
- Wizyta znika z mojej listy nadchodzących
- Widzę ją w historii jako "Odwołana"
```

### US-002: One-click cancellation z e-maila

```gherkin
Jako zajęty klient
Chcę odwołać wizytę jednym kliknięciem z e-maila
Aby nie tracić czasu na logowanie

Acceptance Criteria:
- E-mail z przypomnieniem zawiera link "Odwołaj"
- Kliknięcie przenosi do strony odwołania
- Nie wymaga logowania (token URL)
- Widzę potwierdzenie od razu
- Otrzymuję e-mail z potwierdzeniem odwołania
```

### US-003: Re-booking po odwołaniu

```gherkin
Jako klient który odwołał wizytę
Chcę od razu zarezerwować nowy termin
Aby nie tracić dwukrotnie czasu na rezerwację

Acceptance Criteria:
- Po odwołaniu widzę sugestie nowych terminów
- Mogę zarezerwować jednym kliknięciem
- Mogę dodać się do listy oczekujących
- Otrzymuję powiadomienie gdy slot się zwolni
```

### US-004: Obsługa odwołuje w imieniu klienta

```gherkin
Jako pracownik obsługi
Chcę odwołać wizytę dla dzwoniącego klienta
Aby obsłużyć jego prośbę

Acceptance Criteria:
- Mogę odwołać w każdym momencie (nawet <24h)
- Mogę zaznaczyć powód
- Mogę wysłać powiadomienie do klienta
- Mogę od razu zarezerwować nowy termin
- Widzę log kto i kiedy odwołał
```

## UX/UI Guidelines

### Lista wizyt klienta

```text
┌─────────────────────────────────────┐
│  Moje nadchodzące wizyty            │
├─────────────────────────────────────┤
│  ┌───────────────────────────────┐ │
│  │ Strzyżenie damskie            │ │
│  │ 15 grudnia 2025, 14:00        │ │
│  │ Czas: 30 min • Cena: 80 PLN   │ │
│  │                               │ │
│  │ Możesz odwołać do: 14.12 14:00│ │
│  │ [Szczegóły] [Odwołaj]         │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Koloryzacja                   │ │
│  │ 20 grudnia 2025, 16:00        │ │
│  │ ⏰ Za późno na odwołanie!     │ │
│  │ (mniej niż 24h przed wizytą)  │ │
│  │ Zadzwoń: +48 123 456 789      │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Komunikaty

**Sukces:**
- ✅ "Wizyta odwołana pomyślnie"
- ✅ "Wysłaliśmy potwierdzenie na Twój e-mail"

**Ostrzeżenia:**
- ⚠️ "Do wizyty zostało 20 godzin. Możesz odwołać, ale slot może być trudny do zapełnienia"
- ⚠️ "Już odwołałeś 2 wizyty w tym miesiącu"

**Błędy:**
- ❌ "Za późno na odwołanie (mniej niż 24h). Zadzwoń do salonu"
- ❌ "Wizyta już się odbyła. Nie można odwołać"

## Metryki sukcesu

### KPI

- **No-show reduction:** -50% w 3 miesiące
- **Advance cancellation:** >80% odwołań >24h przed
- **Re-fill rate:** >60% odwołanych slotów zapełnionych ponownie
- **Cancellation rate:** <15% wszystkich rezerwacji

### Tracking

- Powód odwołań (top 3)
- Średni czas odwołania przed wizytą
- % klientów używających one-click vs logowanie
- % klientów re-bookujących po odwołaniu

## Konsekwencje

### Pozytywne

- ✅ Łatwiejsze odwoływanie = mniej no-show
- ✅ Wcześniejsze odwołania = więcej czasu na zapełnienie
- ✅ Automatyzacja procesu
- ✅ Lepsza UX dla klientów

### Negatywne

- ⚠️ Klienci mogą nadużywać łatwości odwoływania
- ⚠️ Późne odwołania nadal możliwe (przez obsługę)
- ⚠️ Wymaga monitorowania abuse

### Mitigacje

**Abuse prevention:**
- Flagowanie klientów z >50% odwołań
- Wymóg przedpłaty dla problematycznych klientów (Faza 2)
- Limit odwołań (np. max 3/miesiąc) - opcjonalnie

**Late cancellations:**
- Komunikaty edukacyjne o 24h zasadzie
- Progressbar pokazujący deadline
- Push notifications przypominające o wizycie

## Implementacja

### Faza 1: MVP (Miesiąc 1)

- Odwoływanie przez klienta (logowanie)
- Odwoływanie przez obsługę
- Powiadomienia e-mail
- Zasada 24h

### Faza 2: Rozszerzenie (Miesiąc 2)

- One-click z e-maila (token URL)
- Re-booking suggestions
- Lista oczekujących
- Historia odwołań

### Faza 3: Zaawansowane (Miesiąc 3+)

- System punktowy
- Przedpłaty dla problematycznych klientów
- Auto-fill z listy oczekujących
- Analityka przyczyn odwołań

## Odniesienia

- Booking.com cancellation policy - best practices
- OpenTable no-show prevention strategies
- Internal data: 30% no-show, 60% mogłoby odwołać online gdyby było łatwiej
