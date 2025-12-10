# Główne funkcjonalności

## Strona główna

- Link do rejestracji

## Rejestracja użytkownika na usługę

- Rejestrowanie przez użytkownika
- Rejestrowanie przez obsługę klienta
- Rozpoznawanie klienta po numerze telefonu i/lub adresie e-mail
- Weryfikacja numeru telefonu przez SMS
- Weryfikacja adresu e-mail przez link aktywacyjny
- Historia wizyt
- Data i godzina wizyty
- Rodzaj usługi
- Akceptacja regulaminu

### Flow rejestracja użytkownika na usługę przez klienta

1. Użytkownik wybiera rodzaj usługi
2. Akceptuje regulamin
3. Klient rejestruje się samodzielnie przez interfejs użytkownika
   1. Klient podaje podstawowe dane: imię, nazwisko, numer telefonu, adres e-mail
  2. Dostaje powiadomienie, gdzie został wysłany kod
  3. Jeśli klient nie zdąży użyć kodu, kod zostanie oznaczony jako wygasły
  4. Kod może zostać użyty lub pozostać nieużyty

### Flow rejestracja użytkownika na usługę przez obsługę klienta

- Obsługa klienta rejestruje użytkownika przez interfejs obsługi klienta
- Możliwość wyszukiwania klienta po numerze telefonu, adresie e-mail lub nazwisku i imieniu
- Jeśli klient nie istnieje, możliwość założenia nowego konta podczas rejestracji na usługę
  - Obsługa podaje podstawowe dane: imię, nazwisko, numer telefonu, adres e-mail
- Wysyłanie potwierdzenia rejestracji na e-mail/SMS


## Odwoływanie wizyty

- Odwoływanie przez użytkownika
- Odwoływanie przez obsługę klienta
- Potwierdzenie odwołania zarówno w interfejsie klienta, jak i w interfejsie obsługi klienta

### Flow klienta

1. Użytkownik loguje się na swoje konto
2. Wybiera wizytę do odwołania
3. Potwierdza odwołanie wizyty
4. Otrzymuje potwierdzenie odwołania wizyty na e-mail/SMS
5. Wizyta powinna zostać zaznaczona jako odwołana w systemie
6. Obsługa dostaje powiadomienie o odwołaniu wizyty

### Flow obsługi

1. Obsługa klienta loguje się do systemu
2. Wybiera klienta po numerze telefonu, adresie e-mail lub nazwisku i imieniu
3. Wybiera jego wizytę do odwołania
4. Potwierdza odwołanie wizyty
5. Klient otrzymuje potwierdzenie odwołania wizyty na e-mail/SMS
6. Wizyta powinna zostać zaznaczona jako odwołana w systemie
7. Zaznaczenie daty i godziny odwołania (opcjonalne)
8. Obsługa dostaje potwierdzenie o odwołaniu wizyty
9. Wybranie statusu wizyty (zaplanowana, odwołana, zrealizowana)

## Dodawanie usług klienta

- Nazwa (opis i zdjęcie) i cena
- Czas trwania zależny od rodzaju usługi
- Wybór dodatkowych opcji

## Dodawanie usług obsługi klienta

 - Dodawanie nowych usług, zdjęć i opisów
 - Ustawianie czasu trwania usługi (np. 30 / 45 / 60 minut)
 - Ustawianie ceny usługi
 - Nadawanie koloru/ikony usłudze (łatwiejsze rozróżnianie w kalendarzu)
 - Usuwanie usług


## Dodawanie terminów klienta

- Podgląd dostępnych terminów dla wybranej usługi
- Filtrowanie terminów po dacie i/lub godzinie
- Wybór konkretnego terminu wizyty
- Podgląd swoich zaplanowanych wizyt (nadchodzące terminy)
- Odwołanie wizyty w dozwolonym czasie (zgodnie z regulaminem)


## Dodawanie terminów obsługi klienta

- Dodawanie nowych terminów dla wybranych usług
- Dodawanie cyklicznych terminów (np. pon–pt 9:00–17:00 co 30 minut)
- Ustawianie godziny rozpoczęcia i czasu trwania terminu
- Status terminu (dostępny / zajęty / zablokowany).
- Edycja istniejących terminów (zmiana godziny, usługi, limitu miejsc)
- Usuwanie lub blokowanie terminów (np. urlop, niedostępność)
- Kopiowanie terminów na kolejne dni lub tygodnie