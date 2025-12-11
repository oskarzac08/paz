# PDR-006: Zarządzanie terminami i cykliczne sloty

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Obsługa potrzebuje efektywnego sposobu na tworzenie dostępności w systemie:

- Manualne dodawanie każdego slotu = nieefektywne
- Powtarzalny grafik pracy (np. pon-pt 9-17)
- Specjalne dni (urlopy, święta, szkolenia)
- Różne usługi = różne czasy slotów

### Potrzeby użytkowników

**Obsługa/Manager:**

- Szybkie tworzenie tygodniowego grafiku
- Kopiowanie slotów na następne tygodnie/miesiące
- Blokowanie terminów (urlop, przerwy)
- Edycja godzin otwarcia
- Różne sloty dla różnych usług

## Decyzja

Implementujemy **zaawansowany system zarządzania terminami**:

### 1. Tworzenie pojedynczego slotu

**Prosty formularz:**

```text
┌─────────────────────────────────────┐
│  Dodaj termin                       │
├─────────────────────────────────────┤
│  Usługa:                            │
│  ▼ [Wybierz usługę]                 │
│                                     │
│  Data:                              │
│  [📅 15.12.2025]                    │
│                                     │
│  Godzina rozpoczęcia:               │
│  [🕐 09:00]                         │
│                                     │
│  Czas trwania:                      │
│  ○ 30 min  ○ 45 min  ○ 60 min      │
│  (automatycznie z usługi: 30 min)  │
│                                     │
│  Status:                            │
│  ○ Dostępny  ○ Zablokowany         │
│                                     │
│  [Anuluj]  [Dodaj termin]          │
└─────────────────────────────────────┘
```

### 2. Tworzenie cyklicznych slotów

**Zaawansowany formularz:**

```text
┌─────────────────────────────────────┐
│  Dodaj cykliczne terminy            │
├─────────────────────────────────────┤
│  Usługa:                            │
│  ▼ [Strzyżenie damskie - 30min]    │
│                                     │
│  Zakres dat:                        │
│  Od: [📅 13.12.2025]               │
│  Do: [📅 31.12.2025]               │
│                                     │
│  Dni tygodnia:                      │
│  ☑ Pon  ☑ Wt  ☑ Śr  ☑ Czw  ☑ Pt  │
│  ☐ Sob  ☐ Nie                      │
│                                     │
│  Godziny:                           │
│  Od: [🕐 09:00]  Do: [🕐 17:00]   │
│  Co: ○ 30 min  ○ 60 min            │
│  (automatycznie z usługi)          │
│                                     │
│  Przerwy:                           │
│  ☑ 13:00 - 14:00 (lunch)           │
│  [+ Dodaj przerwę]                 │
│                                     │
│  Podsumowanie:                      │
│  • Dni: 15 (pon-pt)                │
│  • Sloty/dzień: 14 (z przerwą)     │
│  • Razem slotów: 210               │
│                                     │
│  [Anuluj]  [Utwórz sloty]          │
└─────────────────────────────────────┘
```

**Logika:**

- System generuje sloty co X minut (z usługi)
- Pomija przerwy
- Pomija weekendy (jeśli nie zaznaczone)
- Bulk insert do bazy (wydajność)

### 3. Kopiowanie terminów

**Use case:** Powtórzenie grafiku z poprzedniego tygodnia

```text
┌─────────────────────────────────────┐
│  Kopiuj terminy                     │
├─────────────────────────────────────┤
│  Skopiuj terminy z:                 │
│  Od: [📅 06.12.2025]               │
│  Do: [📅 12.12.2025]               │
│                                     │
│  Na okres:                          │
│  Od: [📅 13.12.2025]               │
│  Do: [📅 19.12.2025]               │
│                                     │
│  Opcje:                             │
│  ☑ Kopiuj tylko dostępne sloty     │
│  ☐ Kopiuj zablokowane              │
│  ☑ Pomiń już istniejące            │
│                                     │
│  [Anuluj]  [Kopiuj]                │
└─────────────────────────────────────┘
```

### 4. Blokowanie terminów

**Scenariusze:**

- Urlop (blokuj wszystkie sloty w zakresie dat)
- Przerwa techniczna (blokuj konkretne godziny)
- Szkolenie (blokuj dzień)

```text
┌─────────────────────────────────────┐
│  Zablokuj terminy                   │
├─────────────────────────────────────┤
│  Typ blokady:                       │
│  ○ Urlop (cały dzień)              │
│  ○ Przerwa (wybrane godziny)       │
│  ○ Wydarzenie specjalne            │
│                                     │
│  Zakres dat:                        │
│  Od: [📅 20.12.2025]               │
│  Do: [📅 27.12.2025]               │
│                                     │
│  (Dla przerwy) Godziny:            │
│  Od: [  -  ]  Do: [  -  ]          │
│                                     │
│  Powód (widoczny dla obsługi):     │
│  [Urlop świąteczny]                │
│                                     │
│  Akcja dla istniejących rezerwacji:│
│  ○ Oznacz jako do przełożenia      │
│  ○ Odwołaj automatycznie           │
│  ○ Pozostaw bez zmian              │
│                                     │
│  [Anuluj]  [Zablokuj]              │
└─────────────────────────────────────┘
```

### 5. Widok kalendarza obsługi

**Zarządzanie slotami:**

```text
┌──────────────────────────────────────────────┐
│  Zarządzanie terminami   [+ Nowy] [Kopiuj]   │
├──────────────────────────────────────────────┤
│  Poniedziałek, 13.12.2025                    │
│  ┌────────────────────────────────────────┐ │
│  │ 09:00  [Strzyżenie D - 30min] ✓        │ │
│  │ 09:30  [Strzyżenie D - 30min] ✓        │ │
│  │ 10:00  [Strzyżenie D - 30min] 🔒       │ │
│  │        (Jan Kowalski - Zarezerwowane)  │ │
│  │ 10:30  [Strzyżenie D - 30min] ✓        │ │
│  │ ...                                     │ │
│  │ 13:00  ⏸ PRZERWA                       │ │
│  │ 14:00  [Strzyżenie D - 30min] ✓        │ │
│  │ ...                                     │ │
│  │ 17:00  [Koniec dnia]                   │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  Legenda:                                    │
│  ✓ Dostępny  🔒 Zarezerwowany  ⏸ Przerwa  │
└──────────────────────────────────────────────┘
```

**Akcje na slocie:**

- Kliknięcie → edycja/blokada/usunięcie
- Drag & drop → zmiana godziny (przyszłość)
- Bulk actions → zaznacz wiele → zablokuj/usuń

### 6. Template grafików

**Zapisane szablony:**

```text
Szablon: "Standardowy tydzień"
- Pon-Pt: 9:00-17:00
- Przerwa: 13:00-14:00
- Sloty: co 30 min
- Usługi: Strzyżenie D, Strzyżenie M

[Zastosuj szablon na: grudzień 2025]
```

**Korzyści:**

- Szybkie setup nowego miesiąca
- Spójność grafików
- Mniej błędów

## Uzasadnienie

### Dlaczego cykliczne tworzenie?

- **Efektywność:** 1 formularz = 200+ slotów
- **Consistency:** Powtarzalny grafik
- **Czas:** 5 minut vs 2 godziny manualnie

### Dlaczego kopiowanie?

- **Convenience:** Grafik często się powtarza
- **Speed:** Szybsze niż re-tworzenie
- **Flexibility:** Można modyfikować po skopiowaniu

### Dlaczego blokowanie?

- **Planning:** Urlopy, przerwy, wydarzenia
- **Prevention:** Nie można zarezerwować zablokowanego
- **Communication:** Klient widzi "Niedostępne" zamiast pustego dnia

## User Stories

### US-001: Tworzenie tygodniowego grafiku

```gherkin
Jako manager
Chcę utworzyć grafik na cały tydzień jednym formularzem
Aby zaoszczędzić czas

Acceptance Criteria:
- Formularz dla cyklicznych slotów
- Wybór dni tygodnia
- Zakres godzin i interwał
- Definicja przerw
- Podgląd liczby slotów przed utworzeniem
- Tworzenie 200+ slotów w <10 sekund
```

### US-002: Blokowanie urlopu

```gherkin
Jako manager
Chcę zablokować wszystkie terminy podczas urlopu
Aby klienci nie rezerwowali w tym czasie

Acceptance Criteria:
- Wybór zakresu dat
- Automatyczne oznaczenie slotów jako zablokowanych
- Opcja akcji dla istniejących rezerwacji
- Powiadomienie klientów z rezerwacjami
```

## Metryki sukcesu

### KPI

- **Setup time:** <10 minut dla miesięcznego grafiku
- **Slot utilization:** >70% slotów zapełnionych
- **Error rate:** <1% (conflicting slots)

## Konsekwencje

### Pozytywne

- ✅ Dramatyczna redukcja czasu setup
- ✅ Mniej błędów
- ✅ Elastyczność
- ✅ Łatwe planowanie

### Negatywne

- ⚠️ Złożoność UI (wiele opcji)
- ⚠️ Bulk operations = trudne do cofnięcia
- ⚠️ Wymaga szkolenia

### Mitigacje

- Wizard dla początkujących
- Confirm dialogs dla bulk actions
- Undo functionality (w przyszłości)

## Implementacja

### Faza 1: MVP

- Pojedyncze sloty
- Cykliczne (podstawowe)
- Blokowanie

### Faza 2: Enhancement

- Kopiowanie
- Szablony
- Bulk edit

### Faza 3: Advanced

- Drag & drop
- AI suggestions (based on demand)
- Multi-location support

## Odniesienia

- Calendly - availability management
- Google Calendar - recurring events
- Square Appointments - staff scheduling
