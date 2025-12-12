# PDR-002: Proces rezerwacji wizyt przez klienta

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Klienci potrzebują prostego i intuicyjnego sposobu na rezerwację wizyt online, który:

- Minimalizuje czas potrzebny na dokonanie rezerwacji
- Jasno pokazuje dostępne terminy
- Daje pewność, że rezerwacja została przyjęta
- Nie wymaga kontaktu telefonicznego z obsługą

Obecna sytuacja (rezerwacje telefoniczne):

- Długi czas oczekiwania na połączenie
- Ograniczone godziny obsługi telefonicznej
- Brak możliwości rezerwacji poza godzinami pracy
- Frustracja klientów przy zajętej linii

### Potrzeby użytkowników

**Klient:**

- Chce zobaczyć dostępne terminy bez kontaktu z obsługą
- Potrzebuje filtrowania po dacie i godzinie (dopasowanie do swojego kalendarza)
- Oczekuje jasnego potwierdzenia rezerwacji
- Chce móc zarezerwować wizytę o dowolnej porze (24/7)
- Potrzebuje informacji o czasie trwania i cenie

## Decyzja

Implementujemy **4-krokowy proces rezerwacji** z następującym flow:

### Krok 1: Wybór usługi

**Widok:** Katalog usług z kafelkami

**Elementy:**

- Zdjęcie usługi
- Nazwa usługi
- Krótki opis (2-3 zdania)
- Czas trwania (np. "30 min")
- Cena (np. "150 PLN")
- Przycisk "Wybierz"

**Sortowanie/Filtrowanie:**

- Alfabetycznie
- Po cenie (rosnąco/malejąco)
- Po czasie trwania
- Kategorie usług (jeśli >10 usług)

### Krok 2: Wybór terminu

**Widok:** Kalendarz + lista dostępnych godzin

**Elementy:**

- Kalendarz miesięczny (oznaczenie dni z dostępnością)
- Po wybraniu dnia: lista dostępnych godzin
- Filtr: "Pokaż tylko poranki/popołudnia/wieczory"
- Informacja: "Następny dostępny: jutro, 14:00"

**Kolory w kalendarzu:**

- Zielony: Dostępne terminy
- Szary: Brak dostępności
- Nieaktywny: Dni z przeszłości

**Lista godzin:**

```
□ 09:00 - 09:30  (Dostępne)
□ 09:30 - 10:00  (Dostępne)
■ 10:00 - 10:30  (Zajęte)
□ 10:30 - 11:00  (Dostępne)
```

### Krok 3: Podsumowanie i regulamin

**Widok:** Podsumowanie rezerwacji + akceptacja regulaminu

**Elementy:**

- Podsumowanie:
  - Usługa: [Nazwa]
  - Data: [DD.MM.YYYY]
  - Godzina: [HH:MM - HH:MM]
  - Czas trwania: [XX min]
  - Cena: [XXX PLN]
- Checkbox: "Akceptuję regulamin" (z linkiem do regulaminu)
- Przycisk "Potwierdź rezerwację"
- Link "Wróć i zmień termin"

**Walidacja:**

- Regulamin musi być zaakceptowany
- Termin nadal dostępny (sprawdzenie w backend)

### Krok 4: Potwierdzenie

**Widok:** Ekran potwierdzenia z detalami

**Elementy:**

- ✅ Ikona sukcesu
- "Rezerwacja potwierdzona!"
- Szczegóły wizyty (jak w podsumowaniu)
- "Wysłaliśmy potwierdzenie na: email@example.com"
- Przyciski:
  - "Dodaj do kalendarza" (.ics file)
  - "Przejdź do moich wizyt"
  - "Zarezerwuj kolejną wizytę"

### Dodatkowe funkcjonalności

**Breadcrumbs:** Pokazywanie postępu

```
[1. Usługa] → [2. Termin] → [3. Podsumowanie] → [4. Potwierdzenie]
   ✓              ✓              >                  
```

**Zapisywanie stanu:** Jeśli użytkownik wyjdzie, powrót do ostatniego kroku

**Mobile-first:** Responsywny design, touch-friendly

## Uzasadnienie

### Dlaczego 4 kroki?

- **Klarowność:** Każdy krok ma jeden cel
- **Progres:** Użytkownik widzi postęp
- **Walidacja:** Możliwość sprawdzenia na każdym etapie
- **Standard:** Znany z e-commerce (checkout flow)

### Dlaczego kalendarz + lista godzin?

- **Wizualna dostępność:** Szybki przegląd wolnych dni
- **Precyzja:** Lista godzin dla dokładnego wyboru
- **Mobile-friendly:** Kalendarz dobrze działa na touch
- **Efektywność:** Mniej kliknięć niż sama lista

### Dlaczego obowiązkowa akceptacja regulaminu?

- **Compliance:** Wymóg prawny (RODO, Ustawa o usługach)
- **Ochrona:** Zabezpieczenie przed sporami
- **Transparentność:** Klient wie na co się zgadza
- **Standard:** Oczekiwane w systemach rezerwacyjnych

### Dlaczego eksport .ics?

- **Wygoda:** Automatyczne dodanie do kalendarza
- **Przypomnienie:** Przypomnienia z kalendarza użytkownika
- **Integracja:** Google Calendar, Outlook, Apple Calendar
- **Redukcja no-show:** Wizyta w kalendarzu = mniejsze zapomnienie

## User Stories

### US-001: Rezerwacja wizyty przez klienta

```gherkin
Jako klient
Chcę zarezerwować wizytę online
Aby nie dzwonić do salonu i zarezerwować o dogodnej porze

Acceptance Criteria:
- Widzę wszystkie dostępne usługi
- Po wybraniu usługi widzę kalendarz z dostępnością
- Mogę filtrować terminy po porze dnia
- Po wybraniu terminu widzę podsumowanie
- Muszę zaakceptować regulamin
- Otrzymuję potwierdzenie na e-mail/SMS
- Mogę dodać wizytę do kalendarza
```

### US-002: Filtrowanie dostępnych terminów

```gherkin
Jako klient pracujący 9-17
Chcę filtrować terminy tylko na wieczory
Aby szybko znaleźć termin dopasowany do mojego grafiku

Acceptance Criteria:
- Widzę filtry: "Rano (6-12)", "Popołudnie (12-18)", "Wieczór (18-22)"
- Po wybraniu filtru widzę tylko pasujące terminy
- Mogę wybrać wiele filtrów jednocześnie
- Jeśli brak terminów, widzę komunikat "Brak dostępnych terminów. Spróbuj innego dnia"
```

### US-003: Powiadomienie o potwierdzeniu

```gherkin
Jako klient
Chcę otrzymać potwierdzenie rezerwacji na e-mail
Aby mieć pewność, że wizyta została zarezerwowana

Acceptance Criteria:
- E-mail przychodzi w ciągu 2 minut
- Zawiera: nazwę usługi, datę, godzinę, adres salonu
- Zawiera link do odwołania wizyty
- Zawiera plik .ics do dodania do kalendarza
```

## UX/UI Guidelines

### Krok 1: Wybór usługi (Mobile)

```text
┌─────────────────────────────────────┐
│  ← Wstecz         Rezerwacja        │
├─────────────────────────────────────┤
│  Wybierz usługę                     │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ [IMG]      Strzyżenie damskie │ │
│  │            30 min • 80 PLN    │ │
│  │            [Wybierz >]        │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ [IMG]      Koloryzacja        │ │
│  │            120 min • 250 PLN  │ │
│  │            [Wybierz >]        │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ [IMG]      Stylizacja         │ │
│  │            45 min • 100 PLN   │ │
│  │            [Wybierz >]        │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Krok 2: Wybór terminu (Desktop)

```text
┌──────────────────────────────────────────────────────────┐
│  Wybierz termin dla: Strzyżenie damskie (30 min, 80 PLN) │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─── Grudzień 2025 ─────┐    Dostępne godziny          │
│  │ Pn Wt Śr Cz Pt So Nd │    ┌──────────────────────┐   │
│  │  1  2  3  4  5  6  7 │    │ Czwartek, 12.12.2025 │   │
│  │  8  9 10 11 [12] 13 14│   ├──────────────────────┤   │
│  │ 15 16 17 18 19 20 21 │    │ ○ 09:00 - 09:30      │   │
│  │ 22 23 24 25 26 27 28 │    │ ○ 09:30 - 10:00      │   │
│  │ 29 30 31             │    │ ● 10:00 - 10:30 ✗    │   │
│  └──────────────────────┘    │ ○ 10:30 - 11:00      │   │
│                               │ ○ 14:00 - 14:30      │   │
│  Filtry:                      │ ○ 14:30 - 15:00      │   │
│  □ Rano (6-12)               │ ○ 15:00 - 15:30      │   │
│  □ Popołudnie (12-18)        │                       │   │
│  □ Wieczór (18-22)           │ [  Dalej  ]          │   │
│                               └──────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Krok 3: Podsumowanie

```text
┌─────────────────────────────────────┐
│  Podsumowanie rezerwacji            │
├─────────────────────────────────────┤
│                                     │
│  Usługa:      Strzyżenie damskie   │
│  Data:        12 grudnia 2025      │
│  Godzina:     14:00 - 14:30        │
│  Czas:        30 minut             │
│  Cena:        80 PLN               │
│                                     │
│  ─────────────────────────────────  │
│                                     │
│  ☑ Akceptuję regulamin             │
│     [Zobacz regulamin]             │
│                                     │
│  [  Potwierdź rezerwację  ]        │
│                                     │
│  ← Wróć i zmień termin             │
│                                     │
└─────────────────────────────────────┘
```

### Komunikaty

**Sukces:**

- ✅ "Rezerwacja potwierdzona! Wysłaliśmy szczegóły na Twój e-mail"
- ✅ "Dodano do koszyka. Możesz zarezerwować kolejną usługę"

**Błędy:**

- ❌ "Termin już niedostępny. Wybierz inny termin"
- ❌ "Musisz zaakceptować regulamin"
- ⚠️ "Sesja wygasła. Rozpocznij rezerwację od nowa"

**Informacyjne:**

- ℹ️ "Możesz odwołać wizytę do 24h przed terminem"
- ℹ️ "Następny dostępny termin: jutro, 14:00"

## Metryki sukcesu

### KPI

- **Conversion rate:** >60% użytkowników kończy rezerwację
- **Czas rezerwacji:** <2 minuty średnio
- **Abandon rate:** <40% na dowolnym kroku
- **Mobile usage:** >70% rezerwacji z mobile

### Funnel metrics

```
100% - Wejście na stronę rezerwacji
 85% - Wybór usługi (Krok 1)
 70% - Wybór terminu (Krok 2)
 65% - Przejście do podsumowania (Krok 3)
 60% - Potwierdzenie rezerwacji (Krok 4)
```

### User satisfaction

- **NPS:** >40
- **Łatwość użycia:** >4.5/5
- **Zadowolenie z procesu:** >4.3/5

## Konsekwencje

### Pozytywne dla użytkownika

- ✅ Rezerwacja 24/7 bez kontaktu z obsługą
- ✅ Widoczność dostępności w czasie rzeczywistym
- ✅ Szybki proces (<2 min)
- ✅ Natychmiastowe potwierdzenie
- ✅ Automatyczne przypomnienia

### Pozytywne dla biznesu

- ✅ Redukcja obciążenia telefonicznego
- ✅ Więcej rezerwacji poza godzinami pracy
- ✅ Mniej błędów niż przy rezerwacjach telefonicznych
- ✅ Dane analityczne (popularność terminów/usług)

### Negatywne

- ⚠️ Wymaga stałej aktualizacji dostępności
- ⚠️ Klienci mogą nie znaleźć terminu (frustracja)
- ⚠️ Brak osobistego kontaktu (mniej relacji)
- ⚠️ Potrzeba edukacji starszych klientów

### Mitigacje

**Aktualizacja:** Automatyczna synchronizacja z systemem terminów

**Brak terminów:** Opcja "Powiadom gdy pojawi się termin"

**Relacje:** Możliwość dodania notatki do wizyty, personalizacja e-maili

**Edukacja:** Tutorial przy pierwszej rezerwacji, pomoc obsługi

## Alternatywy rozważone

### 1. Rezerwacja tylko przez formularz

**Odrzucone:**

- Brak natychmiastowego potwierdzenia
- Wymaga przetwarzania przez obsługę
- Dłuższy czas odpowiedzi

### 2. Kalendarz bez listy godzin

**Odrzucone:**

- Mniej precyzyjny wybór
- Więcej kliknięć
- Trudniejszy na mobile

### 3. Rezerwacja bez akceptacji regulaminu

**Odrzucone:**

- Ryzyko prawne
- Brak świadomości klienta o zasadach odwołania
- Nie-standard w branży

### 4. Wielokrokowa rezerwacja (koszyk)

**Rozważane na przyszłość:**

- Pozwala rezerwować wiele usług jednocześnie
- Bardziej skomplikowany UX
- Implementacja w Fazie 2

## Implementacja

### Faza 1: MVP (Miesiąc 1)

- Podstawowy flow 4-krokowy
- Kalendarz + lista godzin
- E-mail z potwierdzeniem
- Mobile responsive

### Faza 2: Ulepszenia (Miesiąc 2-3)

- Filtry zaawansowane
- Zapisywanie stanu rezerwacji
- Eksport .ics
- "Powiadom o dostępności"

### Faza 3: Zaawansowane (Miesiąc 4+)

- Multi-booking (kilka usług naraz)
- Integracja z Google Calendar (OAuth)
- Sugestie terminów oparte na historii
- Chat z obsługą podczas rezerwacji

## Testy A/B planowane

1. **Kalendarz vs Lista** - co szybsze dla użytkownika?
2. **Liczba kroków** - 4 vs 3 (połączenie wyboru + podsumowania)
3. **Pozycja regulaminu** - checkbox na dole vs na górze
4. **CTA text** - "Potwierdź" vs "Zarezerwuj" vs "Umów wizytę"

## Odniesienia

- Booking.com checkout flow - inspiracja dla multi-step
- Calendly - kalendarz z dostępnością
- Google Calendar - UX dla wyboru czasu
- Research: 73% użytkowników preferuje rezerwację online vs telefon (internal survey)
