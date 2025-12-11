# PDR-008: Historia wizyt i profil użytkownika

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Klienci i obsługa potrzebują dostępu do historii wizyt dla:

- **Klient:** Śledzenie swoich wizyt, preferencji, wydatków
- **Obsługa:** Szybki dostęp do historii klienta (last visit, preferences)
- **Business:** Analytics, retention, personalizacja

Brak historii prowadzi do:

- Trudności w zapamiętaniu poprzednich wizyt
- Niemożności śledzenia wydatków
- Braku personalizacji usług
- Utraty kontekstu relacji z klientem

### Potrzeby użytkowników

**Klient:**

- Przegląd wszystkich wizyt (przeszłe, nadchodzące)
- Filtry i sortowanie
- Statystyki (ile wizyt, ile wydał)
- Ulubione usługi
- Łatwy re-booking (powtórz ostatnią wizytę)

**Obsługa:**

- Szybki dostęp do historii podczas rozmowy
- Preferencje klienta (ulubione usługi, styliści)
- Notatki z poprzednich wizyt
- Częstotliwość wizyt
- Customer lifetime value

## Decyzja

Implementujemy **kompletny system historii i profili** z następującymi komponentami:

### 1. Profil użytkownika (klient)

**Dashboard klienta:**

```text
┌──────────────────────────────────────────┐
│  👤 Jan Kowalski                         │
│  jan.kowalski@email.com                  │
│  +48 123 456 789                         │
│  [Edytuj profil]                         │
├──────────────────────────────────────────┤
│  Statystyki                              │
│  ┌────────────┬────────────┬──────────┐ │
│  │ 12 wizyt   │ 960 PLN    │ 🏆 VIP   │ │
│  │ Łącznie    │ Wydano     │ Status   │ │
│  └────────────┴────────────┴──────────┘ │
│                                          │
│  • Klient od: 15.06.2024                │
│  • Ostatnia wizyta: 01.12.2025          │
│  • Średni interwał: 28 dni              │
│  • Ulubiona usługa: Strzyżenie męskie   │
├──────────────────────────────────────────┤
│  Szybkie akcje                           │
│  [📅 Zarezerwuj ponownie]               │
│  [⭐ Ulubiona usługa]                   │
│  [📊 Moje statystyki]                   │
└──────────────────────────────────────────┘
```

### 2. Historia wizyt (klient)

**Widok listy:**

```text
┌──────────────────────────────────────────┐
│  Moje wizyty                             │
│  [Nadchodzące] [Przeszłe] [Wszystkie]   │
├──────────────────────────────────────────┤
│  Nadchodzące (2)                         │
│  ┌────────────────────────────────────┐ │
│  │ 15.12.2025, 14:00                  │ │
│  │ Strzyżenie damskie                 │ │
│  │ 30 min • 80 PLN                    │ │
│  │ Status: ✓ Potwierdzona             │ │
│  │ [Szczegóły] [Odwołaj] [Zmień]     │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Przeszłe (12)                           │
│  ┌────────────────────────────────────┐ │
│  │ 01.12.2025, 14:00                  │ │
│  │ Strzyżenie męskie                  │ │
│  │ Status: ✓ Zrealizowana             │ │
│  │ [Zarezerwuj ponownie] [Szczegóły] │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ 15.11.2025, 10:00                  │ │
│  │ Strzyżenie męskie                  │ │
│  │ Status: ✗ Odwołana                 │ │
│  │ (Zmiana planów)                    │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

**Filtry:**

- Status: Wszystkie / Zrealizowane / Odwołane
- Data: Ostatnie 30 dni / 3 miesiące / Rok / Wszystkie
- Usługa: Wybór z listy

### 3. Szczegóły wizyty

**Rozwinięty widok:**

```text
┌──────────────────────────────────────────┐
│  Szczegóły wizyty                        │
├──────────────────────────────────────────┤
│  📅 Data: 01 grudnia 2025                │
│  🕐 Godzina: 14:00 - 14:30              │
│  💇 Usługa: Strzyżenie męskie           │
│  💰 Cena: 80 PLN                        │
│  ✓ Status: Zrealizowana                 │
├──────────────────────────────────────────┤
│  Szczegóły:                              │
│  • Utworzona: 25.11.2025, 18:30         │
│  • Utworzona przez: Klienta (online)    │
│  • Potwierdzenie wysłane: E-mail        │
│  • Przypomnienie: Tak (24h + 2h)        │
├──────────────────────────────────────────┤
│  Akcje:                                  │
│  [📅 Zarezerwuj tę samą usługę]         │
│  [📧 Wyślij szczegóły na e-mail]        │
│  [💾 Dodaj do ulubionych]               │
└──────────────────────────────────────────┘
```

### 4. Profil klienta (widok obsługi)

**Extended view dla staff:**

```text
┌──────────────────────────────────────────┐
│  Profil klienta - Jan Kowalski          │
├──────────────────────────────────────────┤
│  Dane kontaktowe:                        │
│  📧 jan.kowalski@email.com              │
│  📱 +48 123 456 789                     │
│  Preferowany kontakt: E-mail            │
│  ✓ E-mail zweryfikowany                 │
│  ✓ Telefon zweryfikowany                │
├──────────────────────────────────────────┤
│  Statystyki:                             │
│  • Klient od: 15.06.2024 (6 miesięcy)   │
│  • Liczba wizyt: 12                     │
│  • Zrealizowane: 10                     │
│  • Odwołane: 2 (16.7%)                  │
│  • No-show: 0                           │
│  • Łącznie wydane: 960 PLN              │
│  • Średni interwał: 28 dni              │
│  • Status: 🏆 VIP (>10 wizyt)          │
├──────────────────────────────────────────┤
│  Preferencje:                            │
│  • Ulubiona usługa: Strzyżenie męskie   │
│  • Preferowane godziny: Popołudnia      │
│  • Preferowane dni: Sobota              │
├──────────────────────────────────────────┤
│  Notatki obsługi:                        │
│  • "Preferuje krótkie boksy"            │
│  • "Punktualny klient"                  │
│  [+ Dodaj notatkę]                      │
├──────────────────────────────────────────┤
│  Historia wizyt (ostatnie 5):           │
│  ✓ 01.12.2025 - Strzyżenie męskie      │
│  ✓ 01.11.2025 - Strzyżenie męskie      │
│  ✗ 15.10.2025 - Odwołana                │
│  ✓ 01.10.2025 - Strzyżenie męskie      │
│  ✓ 01.09.2025 - Strzyżenie męskie      │
│  [Zobacz wszystkie]                     │
├──────────────────────────────────────────┤
│  Akcje:                                  │
│  [📅 Nowa rezerwacja dla klienta]       │
│  [✉️ Wyślij wiadomość]                  │
│  [📊 Pełny raport]                      │
└──────────────────────────────────────────┘
```

### 5. Notatki do wizyt

**Dla obsługi:**

```text
┌──────────────────────────────────────────┐
│  Notatka do wizyty                       │
├──────────────────────────────────────────┤
│  Wizyta: 15.12.2025, Strzyżenie damskie │
│  Klient: Anna Nowak                     │
│                                          │
│  Notatka (widoczna dla obsługi):        │
│  ┌────────────────────────────────────┐ │
│  │ Klientka uczulona na amoniak.      │ │
│  │ Używać bezamoniakowej farby.       │ │
│  │ Preferuje ciemniejsze odcienie.    │ │
│  └────────────────────────────────────┘ │
│                                          │
│  Dodana przez: Magda (obsługa)          │
│  Data: 12.12.2025, 16:30                │
│                                          │
│  [Zapisz] [Anuluj]                      │
└──────────────────────────────────────────┘
```

**Widoczność:**

- Notatki widoczne tylko dla obsługi
- Historia notatek (kto, kiedy dodał)
- Notatki przenoszą się do nowych wizyt tego samego klienta (sugestia)

### 6. Re-booking (powtórz wizytę)

**Quick action:**

Po kliknięciu "Zarezerwuj ponownie":

```text
┌──────────────────────────────────────────┐
│  Zarezerwuj ponownie                     │
├──────────────────────────────────────────┤
│  Usługa: Strzyżenie męskie              │
│  (z wizyty 01.12.2025)                  │
│                                          │
│  Wybierz nowy termin:                    │
│  [Kalendarz z dostępnymi terminami]     │
│                                          │
│  Następne dostępne:                      │
│  • Jutro, 14:00                         │
│  • Pojutrze, 10:00                      │
│  • 18.12, 14:00                         │
│                                          │
│  [Wybierz termin]                       │
└──────────────────────────────────────────┘
```

**Benefit:**

- Jedna mniej krok (usługa już wybrana)
- Szybsza rezerwacja dla powracających klientów
- Zwiększa retention

### 7. Customer Segments

**Auto-tagging:**

- 🌟 **New:** <3 wizyty
- 👍 **Regular:** 3-9 wizyt
- 🏆 **VIP:** 10+ wizyt
- ⚠️ **At Risk:** Brak wizyty >90 dni (był regularny)
- 🚫 **Problematic:** >50% odwołań lub no-show

**Use cases:**

- Targetowane powiadomienia (np. "Tęsknimy za Tobą" dla At Risk)
- Specjalne oferty dla VIP
- Wymagana przedpłata dla Problematic
- Welcome discount dla New

### 8. Statystyki i analitics (dla klienta)

**Dashboard statystyk:**

```text
┌──────────────────────────────────────────┐
│  Moje statystyki                         │
├──────────────────────────────────────────┤
│  W tym roku (2025):                      │
│  ┌────────────┬────────────┬──────────┐ │
│  │ 8 wizyt    │ 640 PLN    │ 4 godz.  │ │
│  │ Liczba     │ Wydano     │ Czas     │ │
│  └────────────┴────────────┴──────────┘ │
│                                          │
│  Najpopularniejsze usługi:               │
│  1. Strzyżenie męskie (6 wizyt)         │
│  2. Stylizacja (2 wizyty)               │
│                                          │
│  Wydatki po miesiącach:                  │
│  [Wykres słupkowy]                      │
│                                          │
│  Częstotliwość wizyt:                    │
│  Średnio co 28 dni                      │
│  [Wykres timeline]                      │
└──────────────────────────────────────────┘
```

## Uzasadnienie

### Dlaczego pełna historia?

- **Trust:** Transparentność buduje zaufanie
- **Convenience:** Łatwy dostęp do informacji
- **Personalization:** Dane do personalizacji usług
- **Retention:** Statystyki motywują do powrotu

### Dlaczego notatki obsługi?

- **Continuity:** Różni pracownicy mogą obsłużyć
- **Quality:** Lepsza obsługa = zadowolony klient
- **Personalization:** Zapamiętanie preferencji
- **Safety:** Alergies, uwagi medyczne

### Dlaczego segmentacja?

- **Marketing:** Targeted campaigns
- **Risk management:** Identyfikacja problematic clients
- **Retention:** Early intervention dla at-risk
- **Rewards:** VIP programs

### Dlaczego re-booking?

- **Convenience:** Szybsza rezerwacja
- **Retention:** Łatwość = więcej wizyt
- **Revenue:** Więcej bookings = więcej przychodu

## User Stories

### US-001: Przegląd historii wizyt

```gherkin
Jako klient
Chcę zobaczyć wszystkie moje wizyty
Aby śledzić swoją historię i wydatki

Acceptance Criteria:
- Lista wszystkich wizyt (przeszłe + nadchodzące)
- Filtry po statusie i dacie
- Szczegóły każdej wizyty
- Statystyki (liczba, wydatki)
- Eksport do PDF (opcjonalnie)
```

### US-002: Notatka obsługi

```gherkin
Jako pracownik obsługi
Chcę dodać notatkę o preferencjach klienta
Aby kolejna osoba znała kontekst

Acceptance Criteria:
- Formularz dodawania notatki
- Notatka widoczna tylko dla staff
- Historia notatek (kto, kiedy)
- Notatki sugerowane przy nowej rezerwacji
- Możliwość edycji/usunięcia własnych notatek
```

### US-003: Re-booking

```gherkin
Jako klient regularny
Chcę zarezerwować tę samą usługę co ostatnio
Aby nie wybierać od nowa

Acceptance Criteria:
- Przycisk "Zarezerwuj ponownie" przy przeszłej wizycie
- Automatyczny wybór usługi
- Przejście do wyboru terminu
- Takie samo flow jak normalna rezerwacja
```

## Metryki sukcesu

### KPI

- **Re-booking rate:** >40% klientów używa re-booking
- **Retention:** +20% retention dzięki historii i statystykom
- **Notes usage:** >60% wizyt ma notatki
- **Customer satisfaction:** +15% satisfaction dzięki personalizacji

## Konsekwencje

### Pozytywne

- ✅ Lepsza customer experience
- ✅ Wyższa retention
- ✅ Personalizacja usług
- ✅ Lepsze zarządzanie klientami
- ✅ Data dla analytics

### Negatywne

- ⚠️ Privacy concerns (przechowywanie historii)
- ⚠️ Storage requirements (więcej danych)
- ⚠️ Complexity (więcej UI)

### Mitigacje

- RODO compliance (prawo do usunięcia danych)
- Data retention policy (auto-delete po X latach)
- Opcja ukrycia historii dla klienta (privacy mode)

## Implementacja

### Faza 1: MVP

- Lista wizyt (przeszłe + nadchodzące)
- Podstawowy profil
- Re-booking

### Faza 2: Enhancement

- Notatki obsługi
- Statystyki
- Segmentacja

### Faza 3: Advanced

- Analytics dashboard
- Predictive retention
- Recommendations engine

## RODO Compliance

### Data retention

- Wizyty: Przechowywane bezterminowo (z opt-out)
- Notatki: Przechowywane 5 lat (requirement księgowy)
- Prawo do zapomnienia: Klient może żądać usunięcia
- Export danych: Klient może pobrać swoje dane (JSON/PDF)

## Odniesienia

- Booksy - customer profile best practices
- Treatwell - history and re-booking UX
- Spotify - "Your Year in Review" inspiration for stats
- RODO - data retention requirements
