# PDR-003: Zarządzanie rezerwacjami przez obsługę

## Status

Zaakceptowany

## Kontekst

### Problem biznesowy

Obsługa potrzebuje efektywnego systemu do:

- Rezerwowania wizyt w imieniu klientów (telefon, walk-in)
- Szybkiego wyszukiwania klientów w bazie danych
- Zarządzania wszystkimi rezerwacjami (przeglądanie, edycja, anulowanie)
- Tworzenia kont dla nowych klientów podczas rezerwacji
- Zarządzania terminami (tworzenie, edycja, blokowanie)
- Zarządzania usługami (dodawanie, edycja, aktywacja/deaktywacja)

Obecne wyzwania:

- Brak centralnego systemu (papierowy kalendarz/Excel)
- Trudność w znalezieniu historii klienta
- Double-booking przez błędy manualne
- Brak możliwości analizy danych
- Nieefektywne ręczne dodawanie terminów
- Brak śledzenia zmian i audytu operacji

### Potrzeby użytkowników

**Pracownik obsługi:**

- Szybkie wyszukiwanie klienta po telefonie/e-mail/nazwisku
- Tworzenie rezerwacji w 30 sekund lub mniej
- Widok wszystkich rezerwacji na dany dzień/tydzień/miesiąc
- Możliwość edycji/odwołania rezerwacji klienta
- Notatki do wizyt (specjalne życzenia klienta, uwagi)
- Tworzenie kont dla walk-in klientów
- Dostęp do historii wizyt klienta
- Zarządzanie dostępnością terminów

**Manager:**

- Przegląd wszystkich rezerwacji (filtrowanie, sortowanie)
- Statystyki (popularność usług, wykorzystanie terminów, revenue)
- Historia zmian w rezerwacjach (audit trail)
- Zarządzanie usługami i cenami
- Tworzenie cyklicznych terminów (bulk operations)
- Blokowanie terminów (urlopy, wydarzenia specjalne)
- Identyfikacja problematycznych klientów (no-show, częste odwołania)

## Decyzja

Implementujemy **dedykowany panel obsługi (Staff Panel)** z następującymi funkcjonalnościami, zintegrowany z systemem autoryzacji opartym na Django Groups (zgodnie z ADR-006):

### 1. System autoryzacji i uprawnień

**Role użytkowników:**

Zgodnie z ADR-006, system wykorzystuje wbudowany mechanizm Django Groups:

- **Staff Group:** Pełne uprawnienia do zarządzania (is_staff=True)
  - Wszystkie uprawnienia klienta
  - Zarządzanie usługami (add, change, delete, view Service)
  - Zarządzanie terminami (add, change, delete, view TimeSlot)
  - Zarządzanie wszystkimi rezerwacjami (add, change, delete, view Reservation)
  - Wyszukiwanie i przeglądanie klientów (view User, view UserProfile)
  - Tworzenie kont klientów podczas rezerwacji
  - Dostęp do panelu administracyjnego Django
  
- **Client Group:** Podstawowe uprawnienia
  - Przeglądanie usług i terminów
  - Zarządzanie własnymi rezerwacjami
  - Edycja własnego profilu

**Zabezpieczenia:**

```python
# Decorator dla widoków obsługi
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def staff_dashboard(request):
    """Dashboard dostępny tylko dla personelu"""
    pass
```

**Audit trail:**

Każda akcja obsługi jest logowana:
- Kto wykonał akcję (created_by, cancelled_by)
- Kiedy (created_at, updated_at, cancelled_at)
- Jaką operację (create, update, cancel)

### 2. Dashboard obsługi

**Główny widok:**

```text
┌────────────────────────────────────────────────────────────┐
│  Panel obsługi              [Nowa rezerwacja] [Dodaj termin]│
├────────────────────────────────────────────────────────────┤
│  Dzisiaj: 15 grudnia 2025                                  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Podsumowanie                                               │
│  • Rezerwacje dzisiaj: 8 (6 potwierdzonych, 2 oczekujące) │
│  • Wolne sloty dzisiaj: 12                                 │
│  • Oczekujące potwierdzenia: 2                            │
│  • Odwołane dzisiaj: 1                                     │
│                                                             │
│  🔔 Alerty                                                  │
│  • Walk-in klient oczekuje (5 min temu)                   │
│  • 2 przypomnienia do wysłania (jutro)                    │
│                                                             │
│  Dzisiejsze wizyty                    Filtr: [Wszystkie ▼] │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🟢 09:00  Jan Kowalski • Strzyżenie męskie          │ │
│  │          tel: +48 123 456 789 • jan@example.com     │ │
│  │          Utworzone przez: Anna (obsługa)            │ │
│  │          [Szczegóły] [Odwołaj] [Kontakt] [Edytuj]  │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ 🟡 09:30  Anna Nowak • Koloryzacja                  │ │
│  │          email: anna@example.com                    │ │
│  │          Notatka: ⚠️ Uczulenie na amoniak           │ │
│  │          Status: Oczekująca potwierdzenia           │ │
│  │          [Szczegóły] [Potwierdź] [Odwołaj]         │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ 🔴 10:00  Piotr Nowak • Stylizacja                  │ │
│  │          tel: +48 987 654 321                       │ │
│  │          Status: Odwołana (przez klienta, 2h temu)  │ │
│  │          Powód: Zmiana planów                       │ │
│  │          [Szczegóły] [Zarezerwuj ponownie]         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  [Pokaż widok kalendarza] [Eksportuj do PDF]              │
└────────────────────────────────────────────────────────────┘
```

**Funkcjonalności dashboardu:**

- **Real-time updates:** Aktualizacja co 30s (optional WebSocket w przyszłości)
- **Quick actions:** Szybkie akcje bez przechodzenia do szczegółów
- **Status colors:** 🟢 Potwierdzona, 🟡 Oczekująca, 🔴 Odwołana, 🔵 Zrealizowana
- **Filtry:** Status, usługa, zakres dat
- **Sortowanie:** Chronologicznie, alfabetycznie po nazwisku
- **Pagination:** 20 wizyt na stronę

### 3. Szybkie wyszukiwanie klienta

**Widok:**

```text
┌─────────────────────────────────────┐
│  Znajdź klienta                     │
├─────────────────────────────────────┤
│  🔍 [Szukaj: telefon, email, nazwa] │
│                                     │
│  Wyniki (live search po 3 znakach): │
│  ┌─────────────────────────────┐   │
│  │ Jan Kowalski                │   │
│  │ +48 123 456 789             │   │
│  │ jan@example.com             │   │
│  │ ──────────────────────────  │   │
│  │ Ostatnia wizyta: 01.12.2025 │   │
│  │ Liczba wizyt: 12            │   │
│  │ Status: ✓ Zweryfikowany     │   │
│  │ ──────────────────────────  │   │
│  │ [Wybierz] [Profil] [Wizyt] │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Anna Kowalska               │   │
│  │ anna.k@example.com          │   │
│  │ Ostatnia wizyta: 15.11.2025 │   │
│  │ [Wybierz] [Profil]          │   │
│  └─────────────────────────────┘   │
│                                     │
│  Nie znaleziono klienta?           │
│  [+ Utwórz nowego klienta]         │
└─────────────────────────────────────┘
```

**Funkcjonalność:**

- **Live search:** Wyniki po wpisaniu 3 znaków (AJAX)
- **Wyszukiwanie po:**
  - Numerze telefonu (z/bez prefiksu +48, z/bez spacji i myślników)
  - Adresie e-mail (partial match, case-insensitive)
  - Imieniu i nazwisku (fuzzy search, tolerancja błędów)
  - ID użytkownika (dla zaawansowanych)
- **Wyniki pokazują:**
  - Dane kontaktowe
  - Ostatnią wizytę
  - Liczbę wizyt (wskaźnik lojalności)
  - Status weryfikacji (email/phone verified)
  - Flagi: ⚠️ no-show history, 🔴 frequent cancellations
- **Quick actions:**
  - Wybierz → przejdź do rezerwacji
  - Profil → pełny profil klienta z historią
  - Historia → lista wszystkich wizyt

**Implementacja (zgodnie z obecnym kodem):**

```python
# views.py - widok wyszukiwania klientów
@staff_member_required
def search_clients(request):
    """AJAX endpoint dla wyszukiwania klientów"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    # Wyszukiwanie po różnych polach
    users = User.objects.filter(
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(profile__phone_number__icontains=query.replace(' ', '').replace('-', ''))
    ).select_related('profile').prefetch_related('reservations')[:10]
    
    results = []
    for user in users:
        last_reservation = user.reservations.filter(
            status__in=['confirmed', 'completed']
        ).order_by('-start').first()
        
        results.append({
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'phone': user.profile.phone_number if hasattr(user, 'profile') else '',
            'last_visit': last_reservation.start.strftime('%d.%m.%Y') if last_reservation else None,
            'total_visits': user.reservations.filter(status='completed').count(),
            'verified': user.profile.is_verified if hasattr(user, 'profile') else False
        })
    
    return JsonResponse({'results': results})
```

### 4. Tworzenie rezerwacji dla klienta

**Flow (5 kroków):**

**Krok 1: Wyszukanie/utworzenie klienta**

Opcja A - Istniejący klient:
- Wyszukanie przez search (jak w sekcji 3)
- Wybierz z listy → przejście do kroku 2

Opcja B - Nowy klient (walk-in):
```text
┌──────────────────────────────────────┐
│  Dodaj nowego klienta                │
├──────────────────────────────────────┤
│  Imię: *                             │
│  [Jan_______________]                │
│                                      │
│  Nazwisko: *                         │
│  [Kowalski__________]                │
│                                      │
│  Telefon: * (sprawdzanie duplikatów) │
│  [+48 123 456 789___]                │
│  ⚠️ Klient z tym numerem już istnieje│
│  [Zobacz klienta]                    │
│                                      │
│  E-mail: *                           │
│  [jan@example.com___]                │
│                                      │
│  Preferowany kontakt:                │
│  ○ E-mail  ○ SMS  ○ Oba             │
│                                      │
│  Notatka (opcjonalnie):              │
│  [Stały klient, preferuje rano]     │
│                                      │
│  □ Wyślij kod weryfikacyjny         │
│  (klient może aktywować konto)       │
│                                      │
│  [Anuluj]  [Dodaj i kontynuuj]      │
└──────────────────────────────────────┘
```

**Funkcjonalność:**
- Auto-walidacja telefonu/e-mail (sprawdzenie czy nie istnieje)
- Automatyczne utworzenie konta User + UserProfile
- Opcjonalne wysłanie kodu weryfikacyjnego (zgodnie z PDR-001)
- Hasło: generowane automatycznie, wysłane na e-mail
- Konto created_by = current staff user (audit)

**Implementacja:**

```python
@staff_member_required
def create_client_account(request):
    """Tworzenie konta klienta przez obsługę"""
    if request.method == 'POST':
        form = StaffCreateClientForm(request.POST)
        if form.is_valid():
            # Sprawdź duplikaty
            phone = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Klient z tym e-mailem już istnieje')
                return redirect('staff:search_clients')
            
            if UserProfile.objects.filter(phone_number=phone).exists():
                messages.error(request, 'Klient z tym numerem już istnieje')
                return redirect('staff:search_clients')
            
            # Utwórz użytkownika
            password = User.objects.make_random_password()
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=password,
                is_active=True  # Aktywny od razu
            )
            
            # Dodaj do grupy Client
            client_group = Group.objects.get(name='Client')
            user.groups.add(client_group)
            
            # Utwórz profil
            profile = UserProfile.objects.create(
                user=user,
                phone_number=phone,
                preferred_contact=form.cleaned_data['preferred_contact']
            )
            
            # Opcjonalnie wyślij dane do logowania
            if form.cleaned_data.get('send_credentials'):
                send_mail(
                    'Twoje konto zostało utworzone',
                    f'Login: {email}\nHasło: {password}\nZmień hasło po pierwszym logowaniu.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email]
                )
            
            messages.success(request, f'Utworzono konto dla {user.get_full_name()}')
            request.session['booking_client_id'] = user.id
            return redirect('staff:booking_select_service')
    else:
        form = StaffCreateClientForm()
    
    return render(request, 'staff/create_client.html', {'form': form})
```

**Krok 2: Wybór usługi**

```text
┌──────────────────────────────────────┐
│  Rezerwacja dla: Jan Kowalski        │
│  tel: +48 123 456 789                │
├──────────────────────────────────────┤
│  Wybierz usługę:                     │
│                                      │
│  ○ Strzyżenie męskie (30min, 80 PLN)│
│  ○ Strzyżenie damskie (45min, 120 PLN)│
│  ○ Koloryzacja (90min, 300 PLN)     │
│  ○ Stylizacja (60min, 150 PLN)      │
│                                      │
│  lub                                 │
│                                      │
│  ☑ Zablokuj slot bez usługi          │
│  (przerwa, rezerwacja specjalna)     │
│  Powód: [Przerwa techniczna______]  │
│                                      │
│  [Wstecz]  [Dalej]                  │
└──────────────────────────────────────┘
```

**Krok 3: Wybór terminu**

Widok kalendarza (podobny do klienta z PDR-002):
- Kalendarz miesięczny z oznaczeniem dostępności
- Po wyborze dnia: lista dostępnych godzin
- Oznaczenie slotów: ✓ Dostępny, 🔒 Zajęty, ⏸ Przerwa

**Dodatkowe opcje dla obsługi:**
- Podgląd wszystkich slotów (także zajętych - do przełożenia)
- Możliwość utworzenia nowego slotu "on the fly"
- Override: możliwość rezerwacji na zajętym slocie (z ostrzeżeniem)

**Krok 4: Dodatkowe opcje i notatki**

```text
┌──────────────────────────────────────┐
│  Podsumowanie rezerwacji              │
├──────────────────────────────────────┤
│  Klient: Jan Kowalski                │
│  Usługa: Strzyżenie męskie           │
│  Termin: 16.12.2025, 10:00-10:30     │
│  Cena: 80 PLN                        │
├──────────────────────────────────────┤
│  Opcje:                              │
│  ☑ Wyślij potwierdzenie do klienta   │
│     (e-mail/SMS)                     │
│  ☑ Oznacz jako "Potwierdzona"        │
│  ☐ Wymaga przedpłaty                 │
│                                      │
│  Notatka dla obsługi (opcjonalnie):  │
│  ┌─────────────────────────────────┐│
│  │Klient prosi o konkretnego       ││
│  │stylistę - Annę                  ││
│  └─────────────────────────────────┘│
│                                      │
│  Utworzona przez: Maria Nowak        │
│  (bieżący użytkownik obsługi)        │
│                                      │
│  [Wstecz]  [Potwierdź rezerwację]   │
└──────────────────────────────────────┘
```

**Krok 5: Potwierdzenie**

```text
┌──────────────────────────────────────┐
│  ✅ Rezerwacja utworzona!            │
├──────────────────────────────────────┤
│  Rezerwacja #12345                   │
│  Klient: Jan Kowalski                │
│  Usługa: Strzyżenie męskie           │
│  Termin: 16.12.2025, 10:00           │
│                                      │
│  ✓ Potwierdzenie wysłane na e-mail   │
│  ✓ Slot oznaczony jako zajęty        │
│  ✓ Rezerwacja dodana do kalendarza   │
│                                      │
│  [Dodaj kolejną rezerwację]          │
│  [Wróć do dashboardu]                │
│  [Wydrukuj potwierdzenie]            │
└──────────────────────────────────────┘
```

**Zabezpieczenia:**

```python
# Zgodnie z ADR-004 - zapobieganie double-booking
@staff_member_required
@transaction.atomic
def create_staff_booking(request):
    """Tworzenie rezerwacji przez obsługę"""
    client_id = request.session.get('booking_client_id')
    time_slot_id = request.POST.get('time_slot_id')
    service_id = request.POST.get('service_id')
    
    # SELECT FOR UPDATE - blokada na poziomie bazy
    time_slot = TimeSlot.objects.select_for_update().get(
        id=time_slot_id
    )
    
    # Sprawdź dostępność
    if hasattr(time_slot, 'reservation'):
        messages.error(request, 'Slot już zajęty')
        return redirect('staff:booking_calendar')
    
    # Utwórz rezerwację
    reservation = Reservation.objects.create(
        user=User.objects.get(id=client_id),
        service=Service.objects.get(id=service_id),
        start=time_slot.start,
        end=time_slot.end,
        status='confirmed',
        notes=request.POST.get('notes', ''),
        created_by=request.user  # Audit: kto utworzył
    )
    
    # Link TimeSlot z Reservation
    time_slot.reservation = reservation
    time_slot.save()
    
    # Wyślij powiadomienie
    if request.POST.get('send_confirmation'):
        send_booking_confirmation(reservation)
    
    messages.success(request, f'Utworzono rezerwację #{reservation.id}')
    return redirect('staff:dashboard')
```

### 5. Edycja rezerwacji

**Dostępne akcje:**

- **Zmiana terminu** → wybór nowego slotu (z zachowaniem usługi)
- **Zmiana usługi** → wybór z listy (z przeliczeniem czasu)
- **Dodanie/edycja notatki** → tekstowe pole (markdown support)
- **Zmiana statusu:**
  - Oczekująca potwierdzenia → Potwierdzona
  - Potwierdzona → Zrealizowana (po wizycie)
  - Potwierdzona/Oczekująca → Odwołana
- **Oznaczenie no-show** → specjalny status (dla analityki)

**Widok edycji:**

```text
┌──────────────────────────────────────┐
│  Edycja rezerwacji #12345            │
├──────────────────────────────────────┤
│  Klient: Jan Kowalski                │
│  tel: +48 123 456 789                │
│  email: jan@example.com              │
│  [Zobacz profil] [Historia wizyt]    │
├──────────────────────────────────────┤
│  Usługa: *                           │
│  ▼ [Strzyżenie męskie - 30min, 80PLN]│
│                                      │
│  Termin: *                           │
│  Data: [📅 16.12.2025]              │
│  Godzina: [🕐 10:00]                │
│  [Sprawdź dostępność]                │
│                                      │
│  Status: *                           │
│  ▼ [Potwierdzona]                    │
│     • Oczekująca potwierdzenia       │
│     • Potwierdzona                   │
│     • Zrealizowana                   │
│     • Odwołana                       │
│     • No-show                        │
│                                      │
│  Notatka:                            │
│  ┌─────────────────────────────────┐│
│  │Klient prosi o konkretnego       ││
│  │stylistę - Annę                  ││
│  │UPDATE: Anna potwierdzona        ││
│  └─────────────────────────────────┘│
│                                      │
│  □ Wyślij powiadomienie o zmianie    │
│     (e-mail/SMS do klienta)          │
│                                      │
│  Metadane:                           │
│  Utworzona: 10.12.2025, 14:30       │
│  Przez: Maria Nowak (obsługa)        │
│  Ostatnia zmiana: 12.12.2025, 09:15  │
│  Przez: Anna Kowalska (obsługa)      │
│                                      │
│  [Anuluj]  [Zapisz zmiany]          │
└──────────────────────────────────────┘
```

**Zabezpieczenia i walidacje:**

- **Nie można edytować wizyty która już się odbyła** (status='completed')
- **Przy zmianie terminu:**
  - Sprawdzenie dostępności nowego slotu (select_for_update)
  - Zwolnienie starego slotu
  - Wysłanie powiadomienia do klienta o zmianie
- **Przy zmianie usługi:**
  - Sprawdzenie czy nowy czas trwania mieści się w slocie
  - Ewentualna zmiana duration
- **Audit trail:**
  - Historia zmian zapisywana w logach
  - Kto, kiedy, co zmienił

**Implementacja:**

```python
@staff_member_required
@transaction.atomic
def edit_reservation(request, reservation_id):
    """Edycja rezerwacji przez obsługę"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Sprawdź czy można edytować
    if reservation.status == 'completed':
        messages.error(request, 'Nie można edytować zrealizowanej wizyty')
        return redirect('staff:reservation_detail', pk=reservation_id)
    
    if request.method == 'POST':
        form = StaffEditReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            old_start = reservation.start
            old_service = reservation.service
            
            # Zapisz zmiany
            reservation = form.save(commit=False)
            reservation.updated_by = request.user
            reservation.updated_at = timezone.now()
            reservation.save()
            
            # Log zmian
            if old_start != reservation.start:
                log_change(reservation, 'start', old_start, reservation.start, request.user)
            if old_service != reservation.service:
                log_change(reservation, 'service', old_service, reservation.service, request.user)
            
            # Wyślij powiadomienie o zmianie
            if form.cleaned_data.get('notify_client'):
                send_booking_change_notification(reservation, request.user)
            
            messages.success(request, 'Rezerwacja zaktualizowana')
            return redirect('staff:dashboard')
    else:
        form = StaffEditReservationForm(instance=reservation)
    
    return render(request, 'staff/edit_reservation.html', {
        'form': form,
        'reservation': reservation
    })
```

### 6. Odwoływanie rezerwacji

**Flow (zgodnie z PDR-004):**

1. Wybór rezerwacji (z dashboardu lub profilu klienta)
2. Kliknięcie "Odwołaj wizytę"
3. Modal z potwierdzeniem i dodatkowymi opcjami:

```text
┌──────────────────────────────────────┐
│  Odwołanie wizyty                    │
├──────────────────────────────────────┤
│  Czy na pewno odwołać wizytę?        │
│                                      │
│  Klient: Jan Kowalski                │
│  Usługa: Strzyżenie męskie           │
│  Termin: 16.12.2025, 10:00           │
├──────────────────────────────────────┤
│  Odwołane przez: *                   │
│  ○ Klienta (telefon/wizyta/email)   │
│  ○ Salon (wewnętrzne przyczyny)     │
│  ○ Siła wyższa (choroba, awaria)    │
│                                      │
│  Powód odwołania (opcjonalnie):      │
│  ▼ [Wybierz z listy lub wpisz]      │
│     • Zmiana planów klienta          │
│     • Choroba                        │
│     • Awaria w salonie               │
│     • Inne: [________________]       │
│                                      │
│  Notatka wewnętrzna:                 │
│  ┌─────────────────────────────────┐│
│  │Klient prosił o przełożenie na   ││
│  │następny tydzień                 ││
│  └─────────────────────────────────┘│
│                                      │
│  □ Wyślij powiadomienie do klienta   │
│  □ Zaproponuj alternatywne terminy   │
│  □ Dodaj klienta do listy oczekujących│
│                                      │
│  ⚠️ Akcje po odwołaniu:              │
│  • Slot będzie dostępny dla innych   │
│  • Status zmieniony na "Odwołana"    │
│  • Zapisane: kto i kiedy odwołał     │
│                                      │
│  [Anuluj]  [Potwierdź odwołanie]    │
└──────────────────────────────────────┘
```

4. Po potwierdzeniu:
   - Status rezerwacji → 'cancelled'
   - Zwolnienie slotu → dostępny dla innych
   - Wysłanie powiadomienia (jeśli zaznaczone)
   - Powiadomienie do obsługi (dashboard alert)
   - Zapis w audit trail (cancelled_by, cancelled_at)

**Zabezpieczenia:**

- **Obsługa może odwołać wizytę w każdym momencie** (bez ograniczeń 24h jak klient)
- **Log operacji:**
  ```python
  reservation.cancelled_by = request.user  # Staff user
  reservation.cancelled_at = timezone.now()
  reservation.cancellation_reason = form.cleaned_data['reason']
  reservation.cancellation_notes = form.cleaned_data['notes']
  ```
- **Zwolnienie zasobu:**
  ```python
  time_slot.status = 'available'
  time_slot.save()
  ```

**Powiadomienie do klienta (zgodnie z PDR-004):**

```text
Temat: Wizyta odwołana - 16.12.2025

Witaj Jan,

Twoja wizyta została odwołana:

Usługa: Strzyżenie męskie
Termin: 16 grudnia 2025, godz. 10:00
Odwołano przez: Salon (Anna Kowalska)
Powód: Awaria w salonie
Data odwołania: 15.12.2025, 09:00

Przepraszamy za niedogodności!

Najbliższe dostępne terminy:
• 17.12.2025, 10:00
• 18.12.2025, 14:00
• 19.12.2025, 09:00

[Zarezerwuj nowy termin]

Zespół [Nazwa Salonu]
```

**Implementacja:**

```python
@staff_member_required
@transaction.atomic
def cancel_reservation(request, reservation_id):
    """Odwołanie rezerwacji przez obsługę (zgodnie z PDR-004)"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Sprawdź czy można odwołać
    if reservation.status == 'cancelled':
        messages.warning(request, 'Rezerwacja już odwołana')
        return redirect('staff:reservation_detail', pk=reservation_id)
    
    if reservation.status == 'completed':
        messages.error(request, 'Nie można odwołać zrealizowanej wizyty')
        return redirect('staff:reservation_detail', pk=reservation_id)
    
    if request.method == 'POST':
        form = CancellationForm(request.POST)
        if form.is_valid():
            # Odwołaj rezerwację
            reservation.status = 'cancelled'
            reservation.cancelled_by = request.user  # Staff member
            reservation.cancelled_at = timezone.now()
            reservation.cancellation_reason = form.cleaned_data['reason']
            reservation.cancellation_notes = form.cleaned_data['notes']
            reservation.cancelled_by_party = form.cleaned_data['cancelled_by_party']
            reservation.save()
            
            # Zwolnij slot
            if hasattr(reservation, 'time_slot'):
                reservation.time_slot.status = 'available'
                reservation.time_slot.save()
            
            # Wyślij powiadomienie
            if form.cleaned_data.get('notify_client'):
                send_cancellation_notification(
                    reservation,
                    suggest_alternatives=form.cleaned_data.get('suggest_alternatives')
                )
            
            # Dodaj do waitlist jeśli wybrano
            if form.cleaned_data.get('add_to_waitlist'):
                add_to_waitlist(reservation.user, reservation.service)
            
            # Log dla obsługi
            log_cancellation(reservation, request.user, form.cleaned_data)
            
            messages.success(
                request,
                f'Wizyta odwołana. Powiadomienie wysłane: {form.cleaned_data.get("notify_client")}'
            )
            return redirect('staff:dashboard')
    else:
        form = CancellationForm()
    
    return render(request, 'staff/cancel_reservation.html', {
        'form': form,
        'reservation': reservation
    })
```

### 7. Widok kalendarzowy

**Typy widoków:**

- **Dzienny (Day):** Szczegółowa lista wizyt z godzinami
- **Tygodniowy (Week):** Przegląd całego tygodnia (timeline)
- **Miesięczny (Month):** Ogólne zajętości, liczba wizyt/dzień

**Widok dzienny:**

```text
┌──────────────────────────────────────────────────────────┐
│  📅 Wtorek, 16 grudnia 2025         [Dziś] [◄] [►]       │
│  [Dzień] [Tydzień] [Miesiąc]                     [Print]│
├──────────────────────────────────────────────────────────┤
│  Filtr: [Wszystkie usługi ▼]  Status: [Wszystkie ▼]     │
├──────────────────────────────────────────────────────────┤
│  08:00  ┌────────────────────────────────────────────┐  │
│         │                                             │  │
│  09:00  ├─────────────────────────────────────────────┤ │
│         │ 🟢 09:00-09:30 Jan Kowalski                │  │
│         │    Strzyżenie męskie (80 PLN)              │  │
│         │    📞 +48 123 456 789                      │  │
│  09:30  ├─────────────────────────────────────────────┤ │
│         │ 🟡 09:30-10:15 Anna Nowak                  │  │
│         │    Koloryzacja (300 PLN)                   │  │
│         │    ⚠️ Uczulenie na amoniak                 │  │
│  10:00  │                                             │  │
│         │                                             │  │
│  10:30  ├─────────────────────────────────────────────┤ │
│         │ [WOLNY SLOT - 30min]                       │  │
│         │ [+ Dodaj rezerwację]                       │  │
│  11:00  ├─────────────────────────────────────────────┤ │
│         │ ...                                         │  │
│  13:00  ├─────────────────────────────────────────────┤ │
│         │ ⏸ PRZERWA OBIADOWA                         │  │
│  14:00  ├─────────────────────────────────────────────┤ │
│         │ 🔵 14:00-15:00 Piotr Nowak                 │  │
│         │    Stylizacja (150 PLN) - Zrealizowana     │  │
│  15:00  ├─────────────────────────────────────────────┤ │
│         │ 🔴 15:00-15:45 Maria Kowalska              │  │
│         │    Strzyżenie damskie - Odwołana           │  │
│         │    Powód: Choroba (odwołano 2h temu)       │  │
│  16:00  └─────────────────────────────────────────────┘  │
│                                                           │
│  Podsumowanie dnia:                                      │
│  Rezerwacje: 8 | Zrealizowane: 5 | Odwołane: 1          │
│  Przychód: 1200 PLN | Wolne sloty: 4                    │
└──────────────────────────────────────────────────────────┘
```

**Kolory wizyt:** (zgodnie z PDR-002 i PDR-005)
- 🟢 Potwierdzona
- 🟡 Oczekująca potwierdzenia
- 🔴 Odwołana
- 🔵 Zrealizowana
- ⏸ Przerwa/Blokada

**Kolory według usługi** (opcjonalnie, dla lepszej wizualizacji):
- Kolor tła bloku = kolor przypisany do usługi (z Service.color)
- Np. Strzyżenie = niebieski, Koloryzacja = różowy, itp.

**Funkcje interakcyjne:**

- **Click na wizytę:** Quick view modal z detalami + akcje (Edytuj/Odwołaj/Kontakt)
- **Click na wolny slot:** Szybkie dodanie rezerwacji
- **Drag & drop:** Przeciągnięcie wizyty na inny slot = zmiana terminu (Faza 2)
- **Tooltip (hover):** Szczegóły bez klikania

**Widok tygodniowy:**

```text
┌──────────────────────────────────────────────────────────┐
│  13-19 grudnia 2025                      [Print] [Export]│
├──────────────────────────────────────────────────────────┤
│      │ PON │ WT  │ ŚR  │ CZW │ PT  │ SOB │ NIE │         │
│  09:00│ 2   │ 3   │ 4   │ 2   │ 5   │ 1   │ -   │        │
│  10:00│ 1   │ 2   │ 3   │ 3   │ 2   │ 0   │ -   │        │
│  11:00│ 2   │ 1   │ 2   │ 2   │ 3   │ 1   │ -   │        │
│  ...  │     │     │     │     │     │     │     │        │
│                                                           │
│  Podsumowanie tygodnia:                                  │
│  Rezerwacje: 45 | Zrealizowane: 40 | Odwołane: 3         │
│  Przychód: 5200 PLN | Wykorzystanie: 85%                │
└──────────────────────────────────────────────────────────┘
```

**Filtrowanie:**
- Status (wszystkie/potwierdzone/oczekujące/odwołane/zrealizowane)
- Usługa (dropdown z listą usług)
- Zakres dat (date picker)

**Eksport:**
- **PDF:** Wydruk kalendarza (dla papierowej kopii)
- **Excel/CSV:** Dane do analizy
- **iCal:** Import do zewnętrznego kalendarza

**Implementacja:**

```python
@staff_member_required
def calendar_view(request):
    """Widok kalendarza dla obsługi"""
    view_type = request.GET.get('view', 'day')  # day, week, month
    date = request.GET.get('date', timezone.now().date())
    service_filter = request.GET.get('service', None)
    status_filter = request.GET.get('status', None)
    
    if view_type == 'day':
        # Dzień
        reservations = Reservation.objects.filter(
            start__date=date
        ).select_related('user', 'service').order_by('start')
    elif view_type == 'week':
        # Tydzień
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)
        reservations = Reservation.objects.filter(
            start__date__gte=week_start,
            start__date__lte=week_end
        ).select_related('user', 'service').order_by('start')
    else:
        # Miesiąc
        reservations = Reservation.objects.filter(
            start__year=date.year,
            start__month=date.month
        ).select_related('user', 'service').order_by('start')
    
    # Filtry
    if service_filter:
        reservations = reservations.filter(service_id=service_filter)
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    # Wolne sloty
    available_slots = TimeSlot.objects.filter(
        start__date=date,
        status='available'
    ).order_by('start')
    
    context = {
        'view_type': view_type,
        'date': date,
        'reservations': reservations,
        'available_slots': available_slots,
        'services': Service.objects.filter(is_active=True),
        'summary': calculate_daily_summary(reservations)
    }
    
    return render(request, 'staff/calendar.html', context)
```

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

### 8. Zarządzanie usługami (zgodnie z PDR-005)

**Panel zarządzania usługami (dostęp tylko dla Staff):**

```text
┌─────────────────────────────────────────────────────────┐
│  Zarządzanie usługami                    [+ Nowa usługa]│
├─────────────────────────────────────────────────────────┤
│  Filtr: [Wszystkie ▼]  Status: [Aktywne ▼]  [Szukaj...] │
├─────────────────────────────────────────────────────────┤
│  Lista usług (12)                                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 🟦 Strzyżenie męskie                  ✓ Aktywna  │ │
│  │    30 min • 80 PLN                                │ │
│  │    Rezerwacji: 145 (ostatni miesiąc)              │ │
│  │    [Edytuj] [Deaktywuj] [Zobacz statystyki]      │ │
│  ├───────────────────────────────────────────────────┤ │
│  │ 🟪 Koloryzacja                        ✓ Aktywna  │ │
│  │    90 min • 300 PLN                               │ │
│  │    Rezerwacji: 45                                 │ │
│  │    [Edytuj] [Deaktywuj] [Zobacz statystyki]      │ │
│  ├───────────────────────────────────────────────────┤ │
│  │ 🟨 Strzyżenie specjalne               ✗ Draft    │ │
│  │    60 min • 150 PLN                               │ │
│  │    [Edytuj] [Aktywuj] [Usuń]                     │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Dodawanie/edycja usługi:**

```text
┌─────────────────────────────────────────┐
│  Nowa usługa                            │
├─────────────────────────────────────────┤
│  Nazwa: *                               │
│  [Strzyżenie męskie_____________]       │
│                                         │
│  Opis krótki (widoczny na kafelku):     │
│  [Profesjonalne strzyżenie męskie____]  │
│                                         │
│  Opis pełny (markdown):                 │
│  ┌─────────────────────────────────┐   │
│  │W cenie: mycie, strzyżenie,      │   │
│  │stylizacja                       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Czas trwania: *                        │
│  ▼ [30 minut]                           │
│     15 min, 30 min, 45 min, 60 min...   │
│                                         │
│  Cena: *                                │
│  [80] PLN                               │
│                                         │
│  Kolor (dla kalendarza):                │
│  [🎨 #4A90E2] (niebieski)               │
│                                         │
│  Zdjęcie główne: *                      │
│  [📁 Wybierz plik] lub [Przeciągnij]   │
│  Akceptowane: JPG, PNG, WebP (max 5MB)  │
│                                         │
│  Galeria (opcjonalnie, max 6):          │
│  [ ] [ ] [ ] [ ] [ ] [ ]                │
│                                         │
│  Status:                                │
│  ○ Aktywna (widoczna dla klientów)     │
│  ○ Draft (tylko dla obsługi)           │
│  ○ Nieaktywna (ukryta)                 │
│                                         │
│  [Anuluj]  [Zapisz]                    │
└─────────────────────────────────────────┘
```

**Uprawnienia (zgodnie z ADR-006):**
- Tylko użytkownicy z rolą Staff mogą zarządzać usługami
- Operacje: add_service, change_service, delete_service, view_service

### 9. Zarządzanie terminami (zgodnie z PDR-006)

**Panel terminów:**

```text
┌─────────────────────────────────────────────────────────┐
│  Zarządzanie terminami    [+ Pojedynczy] [+ Cykliczne]  │
├─────────────────────────────────────────────────────────┤
│  Zakres: [13.12 - 19.12.2025 ▼]  Usługa: [Wszystkie ▼] │
├─────────────────────────────────────────────────────────┤
│  Poniedziałek, 13.12.2025            Wolne sloty: 8     │
│  ┌───────────────────────────────────────────────────┐ │
│  │ ✓ 09:00-09:30  Strzyżenie męskie  (Dostępny)     │ │
│  │ ✓ 09:30-10:00  Strzyżenie męskie  (Dostępny)     │ │
│  │ 🔒 10:00-10:30  Strzyżenie męskie  (Zarezerwowany)│ │
│  │    Jan Kowalski - Potwierdzona                    │ │
│  │ ⏸ 13:00-14:00  PRZERWA OBIADOWA                  │ │
│  │ ...                                               │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Akcje:                                                 │
│  [Kopiuj terminy z poprzedniego tygodnia]              │
│  [Zablokuj zakres (urlop)]                             │
│  [Usuń wszystkie wolne sloty w zakresie]               │
└─────────────────────────────────────────────────────────┘
```

**Tworzenie cyklicznych slotów:**

```text
┌─────────────────────────────────────────┐
│  Dodaj cykliczne terminy                │
├─────────────────────────────────────────┤
│  Usługa: *                              │
│  ▼ [Strzyżenie męskie - 30min]          │
│                                         │
│  Zakres dat:                            │
│  Od: [📅 13.12.2025]                   │
│  Do: [📅 31.12.2025]                   │
│                                         │
│  Dni tygodnia:                          │
│  ☑ Pon  ☑ Wt  ☑ Śr  ☑ Czw  ☑ Pt      │
│  ☐ Sob  ☐ Nie                          │
│                                         │
│  Godziny pracy:                         │
│  Od: [🕐 09:00]  Do: [🕐 17:00]       │
│  Co: ○ 30 min  ○ 60 min                │
│  (automatycznie z usługi: 30 min)       │
│                                         │
│  Przerwy:                               │
│  ☑ 13:00 - 14:00 (obiad)               │
│  [+ Dodaj przerwę]                      │
│                                         │
│  Podsumowanie:                          │
│  • Dni robocze: 15 (pon-pt)            │
│  • Sloty/dzień: 14 (pomijając przerwę) │
│  • Razem slotów: 210                    │
│                                         │
│  [Anuluj]  [Utwórz sloty]              │
└─────────────────────────────────────────┘
```

**Blokowanie terminów (urlop, przerwa):**

```text
┌─────────────────────────────────────────┐
│  Zablokuj terminy                       │
├─────────────────────────────────────────┤
│  Typ blokady:                           │
│  ○ Urlop (cały dzień/zakres dni)       │
│  ○ Przerwa (wybrane godziny)           │
│  ○ Wydarzenie specjalne                │
│                                         │
│  Zakres dat:                            │
│  Od: [📅 24.12.2025]                   │
│  Do: [📅 26.12.2025]                   │
│                                         │
│  Powód (widoczny dla obsługi):          │
│  [Święta Bożego Narodzenia___]          │
│                                         │
│  Istniejące rezerwacje (2):             │
│  ⚠️ 24.12, 10:00 - Jan Kowalski        │
│  ⚠️ 25.12, 14:00 - Anna Nowak          │
│                                         │
│  Akcja:                                 │
│  ○ Odwołaj i powiadom klientów         │
│  ○ Oznacz do ręcznego kontaktu         │
│  ○ Pozostaw bez zmian                  │
│                                         │
│  [Anuluj]  [Zablokuj terminy]          │
└─────────────────────────────────────────┘
```

**Implementacja (zgodnie z ADR-004):**

```python
@staff_member_required
def create_recurring_slots(request):
    """Tworzenie cyklicznych slotów przez obsługę"""
    if request.method == 'POST':
        form = RecurringSlotForm(request.POST)
        if form.is_valid():
            service = form.cleaned_data['service']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            weekdays = form.cleaned_data['weekdays']  # [0,1,2,3,4]
            start_hour = form.cleaned_data['start_hour']
            end_hour = form.cleaned_data['end_hour']
            breaks = form.cleaned_data.get('breaks', [])
            
            # Bulk create slotów
            slots_created = TimeSlotService.create_recurring_slots(
                service=service,
                start_date=start_date,
                end_date=end_date,
                time_slots=generate_time_slots(
                    start_hour, 
                    end_hour, 
                    service.duration_minutes,
                    breaks
                ),
                weekdays=weekdays
            )
            
            messages.success(request, f'Utworzono {slots_created} slotów')
            return redirect('staff:manage_timeslots')
    else:
        form = RecurringSlotForm()
    
    return render(request, 'staff/create_recurring_slots.html', {'form': form})
```

### 10. Statystyki i raporty

**Dashboard analityczny (Manager):**

```text
┌─────────────────────────────────────────────────────────┐
│  Statystyki i raporty        Okres: [Ostatnie 30 dni ▼] │
├─────────────────────────────────────────────────────────┤
│  📊 Przegląd                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │Rezerwacje│ │Przychód  │ │Nowi      │ │Wykorzyst.│  │
│  │   145    │ │12,500 PLN│ │klienci   │ │    85%   │  │
│  │  +12%    │ │  +8%     │ │    24    │ │   +3%    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────┤
│  📈 Najpopularniejsze usługi                            │
│  1. Strzyżenie męskie - 62 rezerwacji (42.8%)          │
│  2. Koloryzacja - 34 rezerwacji (23.4%)                │
│  3. Strzyżenie damskie - 28 rezerwacji (19.3%)         │
│                                                         │
│  💰 Przychód według usług                              │
│  1. Koloryzacja - 10,200 PLN                           │
│  2. Strzyżenie męskie - 4,960 PLN                      │
│  3. Stylizacja - 3,750 PLN                             │
├─────────────────────────────────────────────────────────┤
│  🕐 Najbardziej popularne godziny                      │
│  09:00-10:00: 18 rezerwacji                            │
│  14:00-15:00: 16 rezerwacji                            │
│  10:00-11:00: 14 rezerwacji                            │
├─────────────────────────────────────────────────────────┤
│  ⚠️ Problemy                                            │
│  • Odwołania: 12 (8.3%)                                │
│  • No-show: 2 (1.4%)                                   │
│  • Średni czas odwołania: 2.5 dnia przed wizytą        │
│                                                         │
│  [Eksportuj raport PDF] [Eksportuj Excel]              │
└─────────────────────────────────────────────────────────┘
```

**Eksport danych:**
- PDF: Raporty do druku
- Excel/CSV: Szczegółowe dane do analizy
- Zakres dat, filtry usługi, status

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
