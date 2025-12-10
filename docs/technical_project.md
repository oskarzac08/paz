# Elementy potrzebne do realizacji projektu technicznego

## Model klienta

- numer telefonu
- adres e-mail
- imię i nazwisko
- kod aktywacyjny
- status aktywacji (e-mail, SMS)

## Model wizyty klienta

- klient -> Model klienta
- data i godzina wizyty
- rodzaj usługi -> Rodzaje usług
- akceptacja regulaminu
- data odwołania
- status wizyty (zaplanowana, odwołana, zrealizowana)

## Rodzaje usług

- nazwa
- opis
- zdjęcia
- cena
- czas trwania
- ikona
- kolor
- status usługi (aktywna / nieaktywna)

## Model terminu

- data
- godzina rozpoczęcia
- godzina zakończenia
- rodzaj usługi
- status (dostępny / zajęty / zablokowany)
- limit miejsc
- liczba zajętych miejsc

## Model kodów weryfikacyjnych
- kanał(SMS / e-mail) 
- kod
- data wygaśnięcia
- status kodu (użyty / nieużyty)