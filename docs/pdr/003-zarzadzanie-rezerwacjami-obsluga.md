# PDR-003: Zarządzanie rezerwacjami przez obsługę

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Obsługa potrzebuje efektywnego systemu do:

- Rezerwowania wizyt w imieniu klientów (telefon, walk-in)
- Szybkiego wyszukiwania klientów
- Zarządzania wszystkimi rezerwacjami
- Tworzenia kont dla nowych klientów podczas rezerwacji

Obecne wyzwania:

- Brak centralnego systemu (papierowy kalendarz/Excel)
- Trudność w znalezieniu historii klienta
- Double-booking przez błędy manualne
- Brak możliwości analizy danych

### Potrzeby użytkowników

**Pracownik obsługi:**

- Szybkie wyszukiwanie klienta po telefonie/e-mail/nazwisku
- Tworzenie rezerwacji w 30 sekund
- Widok wszystkich rezerwacji na dany dzień
- Możliwość edycji/odwołania rezerwacji klienta
- Notatki do wizyt (specjalne życzenia klienta)

**Manager:**

- Przegląd wszystkich rezerwacji
- Statystyki (popularność usług, wykorzystanie terminów)
- Historia zmian w rezerwacjach

## Decyzja

Implementujemy **dedykowany panel obsługi** z następującymi funkcjonalnościami:

### 1. Dashboard obsługi

**Główny widok:**

```text
┌────────────────────────────────────────────────────────────┐
│  Panel obsługi              [Nowa rezerwacja] [Dodaj termin]│
├────────────────────────────────────────────────────────────┤
│  Dzisiaj: 12 grudnia 2025                                  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Podsumowanie                                               │
│  • Rezerwacje dzisiaj: 8                                   │
│  • Wolne sloty dzisiaj: 12                                 │
│  • Oczekujące potwierdzenia: 2                            │
│                                                             │
│  Dzisiejsze wizyty                                         │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 09:00  Jan Kowalski • Strzyżenie męskie              │ │
│  │        tel: +48 123 456 789                           │ │
│  │        [Szczegóły] [Odwołaj] [Kontakt]               │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ 09:30  Anna Nowak • Koloryzacja                      │ │
│  │        email: anna@example.com                        │ │
│  │        Notatka: Uczulenie na amoniak                 │ │
│  │        [Szczegóły] [Odwołaj] [Kontakt]               │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### 2. Szybkie wyszukiwanie klienta

**Widok:**

```text
┌─────────────────────────────────────┐
│  Znajdź klienta                     │
├─────────────────────────────────────┤
│  🔍 [Szukaj: telefon, email, nazwa] │
│                                     │
│  Wyniki:                            │
│  ┌─────────────────────────────┐   │
│  │ Jan Kowalski                │   │
│  │ +48 123 456 789             │   │
│  │ jan@example.com             │   │
│  │ Ostatnia wizyta: 01.12.2025 │   │
│  │ [Wybierz] [Profil]          │   │
│  └─────────────────────────────┘   │
│                                     │
│  Nie znaleziono klienta?           │
│  [+ Utwórz nowego klienta]         │
└─────────────────────────────────────┘
```

**Funkcjonalność:**

- Live search (wyniki po 3 znakach)
- Wyszukiwanie po:
  - Numerze telefonu (z/bez prefiksu)
  - Adresie e-mail (partial match)
  - Imieniu i nazwisku (fuzzy search)
- Historia wizyt klienta
- Szybki podgląd danych kontaktowych

### 3. Tworzenie rezerwacji dla klienta

**Flow:**

**Krok 1:** Wyszukanie/utworzenie klienta

- Jeśli istnieje → wybierz z listy
- Jeśli nie → formularz szybkiego dodania:
  ```text
  Imię: [______]  Nazwisko: [______]
  Tel: [______]   E-mail: [______]
  Preferowany kontakt: ○ SMS  ○ E-mail
  [Dodaj i kontynuuj]
  ```

**Krok 2:** Wybór usługi i terminu

- Widok kalendarza (jak dla klienta)
- Dodatkowa opcja: "Zablokuj slot bez usługi" (przerwy, rezerwacje specjalne)

**Krok 3:** Dodatkowe opcje

```text
□ Wyślij potwierdzenie do klienta
□ Oznacz jako "Potwierdzona przez telefon"
Notatka (opcjonalna):
[_______________________________]
Np. "Klientka prosi o konkretnego stylistę"
```

**Krok 4:** Potwierdzenie

- Automatyczne wysłanie powiadomienia (jeśli zaznaczone)
- Widoczność w dashboardzie
- Log: "Utworzona przez [Imię Obsługi] o [godzina]"

### 4. Edycja rezerwacji

**Możliwe akcje:**

- **Zmiana terminu** → wybór nowego slotu
- **Zmiana usługi** → wybór z listy
- **Dodanie notatki** → tekstowe pole
- **Oznaczenie statusu:**
  - Potwierdzona
  - Oczekująca potwierdzenia
  - Zrealizowana
  - Odwołana

**Zabezpieczenia:**

- Nie można edytować wizyty, która już się odbyła
- Przy zmianie terminu wysyłka powiadomienia do klienta
- Log wszystkich zmian (audit trail)

### 5. Odwoływanie rezerwacji

**Flow:**

1. Wybór rezerwacji
2. Kliknięcie "Odwołaj"
3. Modal z potwierdzeniem:
   ```text
   Czy na pewno odwołać wizytę?
   
   Klient: Jan Kowalski
   Usługa: Strzyżenie męskie
   Termin: 12.12.2025, 14:00
   
   Powód odwołania (opcjonalnie):
   [_______________________________]
   
   □ Wyślij powiadomienie do klienta
   
   [Anuluj]  [Potwierdź odwołanie]
   ```
4. Zwolnienie slotu → dostępny dla innych
5. Wysłanie powiadomienia (jeśli zaznaczone)

### 6. Widok kalendarzowy

**Typy widoków:**

- **Dzienny:** Szczegółowa lista wizyt
- **Tygodniowy:** Przegląd tygodnia
- **Miesięczny:** Ogólne zajętości

**Kolory wizyt:** Według usługi (z ADR-002)

**Funkcje:**

- Drag & drop dla zmiany terminu
- Quick view (najechanie → tooltip z detalami)
- Filtrowanie po usłudze/statusie
- Eksport do PDF/Excel

### 7. Historia klienta

**Widok profilu klienta:**

```text
┌─────────────────────────────────────────┐
│  Jan Kowalski                           │
│  +48 123 456 789 • jan@example.com     │
├─────────────────────────────────────────┤
│  Statystyki                             │
│  • Liczba wizyt: 12                     │
│  • Pierwsza wizyta: 01.06.2024         │
│  • Ostatnia wizyta: 01.12.2025         │
│  • Średni interwał: 30 dni             │
│  • Ulubiona usługa: Strzyżenie męskie  │
│                                         │
│  Historia wizyt                         │
│  ┌─────────────────────────────────┐   │
│  │ 01.12.2025  Strzyżenie  ✓       │   │
│  │ 01.11.2025  Strzyżenie  ✓       │   │
│  │ 15.10.2025  Stylizacja  ✗       │   │
│  │ (odwołana przez klienta)        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Uzasadnienie

### Dlaczego dedykowany panel dla obsługi?

- **Efektywność:** Funkcje dopasowane do workflow obsługi
- **Bezpieczeństwo:** Separacja uprawnień (klient nie widzi wszystkich danych)
- **UX:** Interfejs zoptymalizowany dla pracy przy komputerze (vs mobile dla klientów)

### Dlaczego szybkie wyszukiwanie?

- **Prędkość:** Klient dzwoni → natychmiastowe znalezienie
- **Wygoda:** Nie trzeba pamiętać dokładnej pisowni
- **Fuzzy search:** Tolerancja na błędy ("Kowalsky" znajdzie "Kowalski")

### Dlaczego notatki do wizyt?

- **Personalizacja:** Zapamiętanie preferencji klienta
- **Komunikacja:** Przekazanie info między zmianami
- **Jakość:** Lepsza obsługa = zadowoleni klienci

### Dlaczego audit trail?

- **Accountability:** Kto i kiedy zmienił rezerwację
- **Debugging:** Śledzenie błędów
- **Compliance:** Wymogi RODO (śledzenie dostępu do danych)

## User Stories

### US-001: Rezerwacja dla dzwoniącego klienta

```gherkin
Jako pracownik obsługi
Chcę szybko zarezerwować wizytę dla dzwoniącego klienta
Aby nie kazać mu czekać na linii

Acceptance Criteria:
- Mogę wyszukać klienta po numerze telefonu w <5 sekund
- Widzę jego historię wizyt
- Mogę dodać rezerwację w 3 krokach
- Klient otrzymuje SMS z potwierdzeniem
- Cały proces <1 minuta
```

### US-002: Walk-in klient bez konta

```gherkin
Jako pracownik obsługi
Chcę utworzyć konto i rezerwację dla nowego klienta jednocześnie
Aby obsłużyć go szybko bez opóźnień

Acceptance Criteria:
- Formularz z minimum pól (imię, nazwisko, telefon)
- Walidacja czy klient już nie istnieje
- Automatyczne utworzenie konta
- Natychmiastowa rezerwacja
- Opcjonalne wysłanie powiadomienia
```

### US-003: Odwołanie wizyty przez obsługę

```gherkin
Jako pracownik obsługi
Chcę odwołać wizytę klienta na jego prośbę
Aby zwolnić termin i powiadomić klienta

Acceptance Criteria:
- Mogę odwołać wizytę w 2 kliknięcia
- Mogę dodać powód odwołania
- Klient otrzymuje powiadomienie
- Slot staje się dostępny
- Zmiana jest zalogowana
```

## UX/UI Guidelines

### Skróty klawiszowe

- `Ctrl + N` - Nowa rezerwacja
- `Ctrl + F` - Szukaj klienta
- `Ctrl + K` - Szybkie komendy
- `/` - Focus na search

### Kolory statusów

- 🟢 Zielony - Potwierdzona
- 🟡 Żółty - Oczekująca
- 🔴 Czerwony - Odwołana
- 🔵 Niebieski - Zrealizowana

### Powiadomienia w UI

```text
✅ Sukces: "Rezerwacja utworzona dla Jan Kowalski"
⚠️ Uwaga: "Klient ma już rezerwację na ten dzień"
❌ Błąd: "Nie można odwołać - wizyta już się odbyła"
```

## Metryki sukcesu

### KPI

- **Czas rezerwacji:** <1 minuta średnio
- **Błędy rezerwacji:** <2% (double-booking, złe dane)
- **Adoption rate:** 100% obsługi używa systemu w ciągu 2 tygodni
- **Search speed:** <2 sekundy do znalezienia klienta

### Operational metrics

- Średnia liczba rezerwacji/dzień przez obsługę
- % rezerwacji utworzonych przez obsługę vs klientów
- Czas szkolenia nowego pracownika obsługi: <1 godzina

## Konsekwencje

### Pozytywne dla obsługi

- ✅ Szybsza obsługa klientów
- ✅ Mniej błędów manualnych
- ✅ Łatwy dostęp do historii klienta
- ✅ Automatyzacja powiadomień

### Pozytywne dla biznesu

- ✅ Więcej rezerwacji (mniej lost calls)
- ✅ Lepsza organizacja pracy
- ✅ Dane analityczne
- ✅ Profesjonalny wizerunek

### Negatywne

- ⚠️ Wymaga przeszkolenia obsługi
- ⚠️ Uzależnienie od systemu (awaria = problem)
- ⚠️ Dodatkowe uprawnienia do zarządzania

### Mitigacje

**Szkolenie:** Video tutorial + live training (2h)

**Awaria:** Backup w Excel, SLA 99.9% uptime

**Uprawnienia:** Role-based access control (pracownik vs manager)

## Alternatywy rozważone

### 1. Ten sam interfejs co dla klientów

**Odrzucone:**

- Brak funkcji specyficznych dla obsługi
- Nie wspiera workflow obsługi
- Wolniejszy niż dedykowany panel

### 2. Osobna aplikacja desktop

**Odrzucone:**

- Wymaga instalacji
- Trudniejsze update'y
- Web app wystarczająca

### 3. Integracja z istniejącym CRM

**Rozważane na przyszłość:**

- Wymaga API i customizacji
- Dodatkowe koszty
- Faza 2-3

## Implementacja

### Faza 1: MVP (Miesiąc 1)

- Dashboard z listą wizyt
- Wyszukiwanie klientów
- Tworzenie rezerwacji
- Podstawowe odwoływanie

### Faza 2: Rozszerzenie (Miesiąc 2)

- Widoki kalendarzowe (tydzień/miesiąc)
- Historia klienta
- Notatki do wizyt
- Eksport danych

### Faza 3: Zaawansowane (Miesiąc 3+)

- Drag & drop w kalendarzu
- Skróty klawiszowe
- Szybkie komendy (Command palette)
- Integracja z systemem POS

## Szkolenie obsługi

### Program szkoleniowy

**Dzień 1: Podstawy (2h)**

- Logowanie i nawigacja
- Wyszukiwanie klientów
- Tworzenie rezerwacji
- Praktyka: 10 rezerwacji testowych

**Dzień 2: Zaawansowane (1h)**

- Odwoływanie i edycja
- Historia klienta
- Notatki i komunikacja
- Troubleshooting

**Follow-up:** Wsparcie przez 2 tygodnie

## Odniesienia

- Salesforce - inspiracja dla interfejsu CRM
- Google Calendar - UX dla zarządzania czasem
- Internal feedback: obsługa potrzebuje max 3 kliknięć dla rezerwacji
