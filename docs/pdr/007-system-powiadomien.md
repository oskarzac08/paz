# PDR-007: System powiadomień i przypomnień

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Skuteczna komunikacja z klientami redukuje no-show i buduje zaangażowanie:

- **No-show problem:** 20-30% wizyt bez powiadomień
- **Customer engagement:** Klienci zapominają o wizytach
- **Service quality:** Brak komunikacji = gorsze doświadczenie
- **Lost revenue:** Niepełne sloty przez zapomnienie

### Potrzeby użytkowników

**Klient:**

- Przypomnienie o nadchodzącej wizycie
- Potwierdzenie po rezerwacji
- Informacja o zmianach
- Preferowany kanał komunikacji

**Obsługa:**

- Alerty o nowych rezerwacjach
- Powiadomienia o odwołaniach
- Raporty dzienne/tygodniowe

## Decyzja

Implementujemy **wielokanałowy system powiadomień** z automatyzacją:

### 1. Typy powiadomień

**Dla klienta:**

| Typ | Kiedy | Kanał | Treść |
|-----|-------|-------|-------|
| Potwierdzenie rezerwacji | Natychmiast po rezerwacji | E-mail/SMS | Szczegóły + link do odwołania |
| Przypomnienie 24h | 24h przed wizytą | E-mail/SMS | Przypomnienie + link do odwołania |
| Przypomnienie 2h | 2h przed wizytą | SMS | Krótkie przypomnienie |
| Potwierdzenie odwołania | Po odwołaniu | E-mail/SMS | Potwierdzenie + sugestie nowych terminów |
| Zmiana wizyty | Po edycji przez obsługę | E-mail/SMS | Nowe dane + link do akceptacji |

**Dla obsługi:**

| Typ | Kiedy | Kanał | Treść |
|-----|-------|-------|-------|
| Nowa rezerwacja | Natychmiast | E-mail | Szczegóły klienta i wizyty |
| Odwołanie przez klienta | Po odwołaniu | E-mail | Info + zwolniony slot |
| Raport dzienny | Codziennie rano | E-mail | Lista wizyt na dziś |
| Raport tygodniowy | Poniedziałki | E-mail | Statystyki tygodnia |

### 2. Szablony powiadomień

**E-mail: Potwierdzenie rezerwacji**

```text
Temat: Potwierdzenie rezerwacji - [Nazwa usługi]

Witaj [Imię],

Dziękujemy za rezerwację! Oto szczegóły Twojej wizyty:

────────────────────────────────
📅 Data: 15 grudnia 2025
🕐 Godzina: 14:00
⏱️ Czas trwania: 30 minut
💇 Usługa: Strzyżenie damskie
💰 Cena: 80 PLN
📍 Adres: ul. Piękna 15, Warszawa
────────────────────────────────

[Dodaj do kalendarza] [Odwołaj wizytę] [Zmień termin]

Co zabrać ze sobą:
• Dokument tożsamości (pierwsze wizyty)
• Zdjęcia inspiracji (opcjonalnie)

Potrzebujesz zmiany terminu?
Możesz odwołać wizytę do 24h przed terminem.

Do zobaczenia!
Zespół [Nazwa Salonu]

─────────────────────────────────
📞 Kontakt: +48 123 456 789
📧 Email: kontakt@salon.pl
🌐 www.salon.pl
```

**SMS: Przypomnienie 24h**

```text
Przypomnienie: Wizyta jutro 15.12 o 14:00
Usługa: Strzyżenie damskie (30min, 80 PLN)
Odwołaj: https://salon.pl/c/abc123
Salon Piękna, ul. Piękna 15
```

**SMS: Przypomnienie 2h**

```text
Za 2h wizyta: Strzyżenie damskie, 14:00
ul. Piękna 15, Warszawa
Do zobaczenia! 💇
Salon Piękna
```

### 3. Harmonogram wysyłki

**Automatyczne (Celery cron jobs):**

- **Codziennie 10:00:** Przypomnienia 24h
- **Co godzinę:** Przypomnienia 2h (check for bookings in 2h)
- **Codziennie 8:00:** Raport dzienny dla obsługi
- **Poniedziałki 9:00:** Raport tygodniowy

**Natychmiastowe (triggered):**

- Po rezerwacji → Potwierdzenie
- Po odwołaniu → Potwierdzenie odwołania
- Po edycji → Powiadomienie o zmianie

### 4. Preferencje komunikacji

**Panel użytkownika:**

```text
┌─────────────────────────────────────┐
│  Ustawienia powiadomień             │
├─────────────────────────────────────┤
│  Preferowany kanał:                 │
│  ○ E-mail                           │
│  ○ SMS                              │
│  ● Oba                              │
│                                     │
│  Powiadomienia:                     │
│  ☑ Potwierdzenie rezerwacji         │
│  ☑ Przypomnienie 24h przed          │
│  ☑ Przypomnienie 2h przed           │
│  ☑ Zmiany w wizytach                │
│  ☐ Oferty promocyjne                │
│  ☐ Newsletter                       │
│                                     │
│  [Zapisz ustawienia]                │
└─────────────────────────────────────┘
```

**RODO Compliance:**

- Opt-in dla marketingu
- Opt-out dostępny w każdym e-mailu
- Transactional emails zawsze (rezerwacje)

### 5. Tracking i analytics

**Dashboard powiadomień:**

```text
Statystyki powiadomień (ostatnie 30 dni)

E-mail:
• Wysłane: 450
• Dostarczone: 445 (98.9%)
• Otwarte: 380 (84.4%)
• Kliknięte: 120 (26.7%)

SMS:
• Wysłane: 320
• Dostarczone: 318 (99.4%)
• Koszt: 64 PLN

Skuteczność:
• Redukcja no-show: -45%
• Engagement rate: 85%
• Opt-out rate: 2%
```

### 6. Retry mechanism

**Dla nieudanych wysyłek:**

- Retry 1: Po 5 minutach
- Retry 2: Po 15 minutach
- Retry 3: Po 1 godzinie
- Fail: Alert do admina

**Status tracking:**

- Pending → Sent → Delivered → Read (email) / Delivered (SMS)
- Failed → Retry → Failed (max 3x) → Admin alert

## Uzasadnienie

### Dlaczego dwa przypomnienia (24h + 2h)?

- **24h:** Czas na odwołanie jeśli trzeba
- **2h:** Last-minute reminder (redukcja zapomnienia)
- **Data:** -60% no-show z dwoma przypomnieniami vs jedno

### Dlaczego wybór kanału przez użytkownika?

- **Preference:** Różne osoby, różne preferencje
- **Cost:** E-mail tańszy, SMS dla pilnych
- **Compliance:** RODO wymaga kontroli nad danymi

### Dlaczego link do odwołania w powiadomieniu?

- **Convenience:** One-click cancellation
- **Early cancellation:** Łatwiejsze = wcześniejsze odwołania
- **Slot recovery:** Więcej czasu na zapełnienie

### Dlaczego tracking i analytics?

- **Optimization:** Które powiadomienia najskuteczniejsze?
- **Cost management:** Monitoring kosztów SMS
- **Deliverability:** Czy e-maile nie trafiają do spam?

## User Stories

### US-001: Przypomnienie o wizycie

```gherkin
Jako klient
Chcę otrzymać przypomnienie o mojej wizycie
Aby jej nie zapomnieć

Acceptance Criteria:
- Przypomnienie 24h przed wizytą
- Przypomnienie 2h przed wizytą
- Przypomnienia na preferowany kanał (e-mail/SMS)
- Zawiera wszystkie szczegóły wizyty
- Zawiera link do odwołania
```

### US-002: Opt-out z przypomnień

```gherkin
Jako klient
Chcę wyłączyć przypomnienia SMS (zostaw e-mail)
Aby nie płacić za SMS

Acceptance Criteria:
- Panel preferencji powiadomień
- Możliwość wyboru kanału
- Możliwość wyłączenia konkretnych typów
- Nie można wyłączyć transactional (potwierdzenia)
- Zmiany działają natychmiast
```

### US-003: Raport dzienny dla obsługi

```gherkin
Jako pracownik obsługi
Chcę otrzymać raport wizyt na dziś rano
Aby przygotować się do pracy

Acceptance Criteria:
- E-mail codziennie o 8:00
- Lista wszystkich wizyt na dziś
- Informacje o kliencie (nazwa, telefon)
- Usługa i godzina
- Link do dashboardu
```

## Metryki sukcesu

### KPI

- **No-show reduction:** -50% po wdrożeniu
- **E-mail open rate:** >80%
- **SMS delivery rate:** >98%
- **Opt-out rate:** <5%
- **Early cancellation:** >90% odwołań >24h przed

### ROI

**Założenia:**

- Średnia wizyta: 100 PLN
- No-show przed: 25% (25 wizyt/100)
- No-show po: 10% (10 wizyt/100)
- Saved revenue: 15 wizyt × 100 PLN = 1,500 PLN/100 wizyt

**Koszty:**

- SMS: 0.15 PLN × 2 (przypomnienia) × 100 wizyt = 30 PLN
- E-mail: ~0 PLN (negligible)

**ROI:** 1,500 PLN saved - 30 PLN cost = **1,470 PLN profit** per 100 bookings

## Konsekwencje

### Pozytywne

- ✅ Dramatyczna redukcja no-show
- ✅ Lepsza customer experience
- ✅ Automatyzacja komunikacji
- ✅ Oszczędność czasu obsługi
- ✅ Measurable impact

### Negatywne

- ⚠️ Koszty SMS (można mitigować e-mailem)
- ⚠️ Spam complaints (rzadkie, ale możliwe)
- ⚠️ Wymaga maintenance template'ów
- ⚠️ Dependency na zewnętrzne serwisy (Twilio, SMTP)

### Mitigacje

- Domyślnie e-mail (cheaper)
- Compliance z RODO (opt-out)
- Monitoring delivery rates
- Backup providers

## Implementacja

### Faza 1: MVP

- E-mail potwierdzenia
- E-mail przypomnienie 24h
- Celery dla automation

### Faza 2: Enhancement

- SMS support
- Przypomnienie 2h
- User preferences panel

### Faza 3: Advanced

- Push notifications (mobile app)
- WhatsApp integration
- AI-powered optimal send time
- Personalization (ML)

## Testing

### A/B Tests planowane

1. **Send time:** 24h vs 48h przypomnienie
2. **Message tone:** Formal vs casual
3. **CTA:** "Odwołaj" vs "Zarządzaj wizytą"
4. **Frequency:** 1 vs 2 vs 3 przypomnienia

## Odniesienia

- Mailchimp - email best practices
- Twilio - SMS delivery optimization
- Research: 2 reminders reduce no-show by 60% (internal data)
- RODO compliance checklist
