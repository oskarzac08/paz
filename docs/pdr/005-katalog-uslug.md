# PDR-005: Katalog usług i prezentacja wizualna

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Klienci potrzebują jasnego i atrakcyjnego prezentowania usług, które:
- Pomaga w wyborze odpowiedniej usługi
- Pokazuje wartość (czas, cena, efekty)
- Buduje zaufanie przez zdjęcia i opisy
- Ułatwia porównanie opcji

### Potrzeby użytkowników

**Klient:**
- Wizualna prezentacja usług (zdjęcia przed/po)
- Przejrzyste informacje o cenie i czasie
- Łatwe porównanie usług
- Mobilny dostęp do katalogu

**Obsługa:**
- Łatwe dodawanie/edycja usług
- Upload zdjęć z opisami
- Zarządzanie cenami i czasem
- Aktywacja/dezaktywacja usług sezonowych

## Decyzja

Implementujemy **wizualny katalog usług** z następującymi elementami:

### 1. Kafelki usług (Grid Layout)

**Desktop (3 kolumny):**
```text
┌─────────┐ ┌─────────┐ ┌─────────┐
│ [Zdjęcie│ │ [Zdjęcie│ │ [Zdjęcie│
│  Usługi]│ │  Usługi]│ │  Usługi]│
│ Nazwa   │ │ Nazwa   │ │ Nazwa   │
│ 30 min  │ │ 45 min  │ │ 60 min  │
│ 80 PLN  │ │ 120 PLN │ │ 200 PLN │
│[Wybierz]│ │[Wybierz]│ │[Wybierz]│
└─────────┘ └─────────┘ └─────────┘
```

**Mobile (1 kolumna):**
- Pełna szerokość ekranu
- Touch-friendly przyciski
- Lazy loading obrazów

### 2. Szczegóły usługi (Modal/Strona)

Po kliknięciu "Zobacz więcej":

```text
┌──────────────────────────────────────┐
│ [Hero Image - Główne zdjęcie usługi] │
├──────────────────────────────────────┤
│ Strzyżenie damskie                   │
│ ⭐⭐⭐⭐⭐ (24 opinie)                │
├──────────────────────────────────────┤
│ Cena: 80 PLN                         │
│ Czas: 30 minut                       │
│ [Zarezerwuj teraz]                   │
├──────────────────────────────────────┤
│ Opis:                                │
│ Profesjonalne strzyżenie z           │
│ konsultacją stylisty. W cenie:       │
│ • Mycie włosów                       │
│ • Strzyżenie                         │
│ • Stylizacja                         │
├──────────────────────────────────────┤
│ [Galeria zdjęć]                      │
│ [img] [img] [img] [img]              │
└──────────────────────────────────────┘
```

### 3. System zarządzania dla obsługi

**Panel dodawania usługi:**

- Nazwa (wymagane)
- Opis krótki (2-3 zdania, widoczny na kafelku)
- Opis pełny (szczegóły, markdown support)
- Cena (PLN)
- Czas trwania (wybór: 15/30/45/60/90/120 min)
- Kategoria (opcjonalnie, jeśli >10 usług)
- Kolor dla kalendarza (hex picker)
- Ikona (wybór z biblioteki FontAwesome/Material Icons)
- Status: ○ Aktywna  ○ Nieaktywna (draft/sezonowa)

**Upload zdjęć:**

- Główne zdjęcie (wymagane)
- Galeria dodatkowych (max 6)
- Drag & drop interface
- Auto-resize do 1200x800px
- Kompresja do max 500KB
- Akceptowane formaty: JPG, PNG, WebP
- Alt text dla dostępności

### 4. Kategorie usług (opcjonalne)

Jeśli >10 usług, grupowanie w kategorie:

```text
┌─────────────────────────────────────┐
│ Kategorie:                          │
│ [Wszystkie] [Strzyżenie] [Kolor]    │
│ [Stylizacja] [Zabiegi]              │
├─────────────────────────────────────┤
│ Strzyżenie (5 usług)                │
│ ┌─────────┐ ┌─────────┐            │
│ │ Damskie │ │ Męskie  │            │
└─────────────────────────────────────┘
```

### 5. Sortowanie i filtrowanie

**Opcje sortowania:**
- Alfabetycznie (A-Z)
- Po cenie (rosnąco/malejąco)
- Po czasie trwania
- Najpopularniejsze (based on bookings)

**Filtry:**
- Zakres cenowy (slider: 0-500 PLN)
- Czas trwania (<30min, 30-60min, >60min)
- Kategoria

### 6. Elementy wizualne

**Kolory usług w systemie:**
- Używane w kalendarzu (wizualne rozróżnienie)
- Używane w potwierdzeniach e-mail
- Spójność UI/UX

**Ikony:**
- Szybka identyfikacja typu usługi
- Używane w mobile (mniej miejsca)
- Accessibility (nie tylko kolor)

## Uzasadnienie

### Dlaczego zdjęcia są krytyczne?

- **Zaufanie:** Pokazanie efektów buduje wiarygodność
- **Wizualizacja:** Klient wie czego się spodziewać
- **Conversion:** Usługi ze zdjęciami mają +40% rezerwacji
- **Standard:** Oczekiwane w branży beauty/wellness

### Dlaczego opcjonalne kategorie?

- **Skalowanie:** Przydatne gdy >10 usług
- **Prostota MVP:** Nie wszystkie salony potrzebują kategorii
- **Flexible:** Łatwe dodanie później

### Dlaczego kolor i ikona dla usługi?

- **Kalendarz:** Wizualne rozróżnienie w schedulu
- **Szybkość:** Obsługa szybciej identyfikuje typ
- **UX:** Lepsze doświadczenie niż samo tekst

## User Stories

### US-001: Przeglądanie katalogu

```gherkin
Jako potencjalny klient
Chcę przeglądać dostępne usługi ze zdjęciami
Aby wybrać odpowiednią dla siebie

Acceptance Criteria:
- Widzę kafelki ze zdjęciami wszystkich aktywnych usług
- Każdy kafelek pokazuje: nazwę, czas, cenę
- Mogę kliknąć "Zobacz więcej" dla szczegółów
- Mogę bezpośrednio kliknąć "Zarezerwuj"
- Wszystko działa na mobile
```

### US-002: Dodawanie usługi przez obsługę

```gherkin
Jako manager salonu
Chcę dodać nową usługę z opisem i zdjęciami
Aby klienci mogli ją rezerwować

Acceptance Criteria:
- Formularz z wszystkimi wymaganymi polami
- Mogę dodać 1-6 zdjęć (drag & drop)
- Zdjęcia są automatycznie optymalizowane
- Mogę wybrać kolor i ikonę
- Mogę zapisać jako draft (nieaktywna)
- Usługa pojawia się w katalogu dla klientów
```

### US-003: Filtrowanie po cenie

```gherkin
Jako klient z budżetem
Chcę filtrować usługi po zakresie cenowym
Aby zobaczyć tylko te które mnie stać

Acceptance Criteria:
- Slider cenowy 0-500 PLN
- Real-time filtering (bez przeładowania)
- Licznik wyników "Znaleziono: 5 usług"
- Możliwość reset filtrów
```

## Metryki sukcesu

### KPI
- **View-to-booking:** >30% odwiedzających katalog rezerwuje
- **Image load time:** <2s dla wszystkich zdjęć
- **Mobile traffic:** >70% ruchu
- **Popular services:** Top 3 mają >50% rezerwacji

### Analytics
- Najpopularniejsze usługi (views + bookings)
- Drop-off rate na widoku szczegółów
- Skuteczność zdjęć (A/B testing)
- Wykorzystanie filtrów

## Konsekwencje

### Pozytywne
- ✅ Profesjonalny wygląd
- ✅ Łatwiejszy wybór dla klientów
- ✅ Wyższa konwersja
- ✅ Elastyczne zarządzanie

### Negatywne
- ⚠️ Wymaga dobrych zdjęć (koszt fotografii)
- ⚠️ Maintenance (aktualizacja zdjęć, cen)
- ⚠️ Storage dla obrazów

### Mitigacje
- Opcja użycia stock photos początkowo
- Kompresja i CDN dla wydajności
- Training dla obsługi w fotografii smartfonem

## Implementacja

### Faza 1: MVP
- Podstawowy grid layout
- Upload zdjęć
- Sortowanie alfabetyczne

### Faza 2: Enhancement
- Kategorie
- Filtry zaawansowane
- Galerie zdjęć

### Faza 3: Advanced
- Reviews/ratings
- Video presentations
- 360° views (dla fryzur)

## Odniesienia
- Treatwell, Booksy - katalogi usług beauty
- E-commerce best practices (product listings)
- Image optimization: WebP, lazy loading, CDN
