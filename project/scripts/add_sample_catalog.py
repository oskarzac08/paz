"""
Skrypt dodający przykładowe usługi, kategorie i zdjęcia do katalogu.
Uruchomienie: python manage.py shell < scripts/add_sample_catalog.py
lub: python manage.py runscript add_sample_catalog (jeśli używasz django-extensions)
"""

import os
import sys
import django

# Setup Django
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from ideas.models import Service, ServiceCategory, ServiceImage
from django.contrib.auth import get_user_model

User = get_user_model()

def create_catalog_data():
    """Tworzy przykładowe dane katalogu usług"""
    
    print("🚀 Tworzenie przykładowego katalogu usług...")
    
    # Kategorie
    print("\n📁 Tworzenie kategorii...")
    cat_hair = ServiceCategory.objects.get_or_create(
        slug='fryzjerstwo',
        defaults={
            'name': 'Fryzjerstwo',
            'description': 'Profesjonalne usługi fryzjerskie dla kobiet i mężczyzn',
            'order': 1,
            'is_active': True
        }
    )[0]
    
    cat_beauty = ServiceCategory.objects.get_or_create(
        slug='kosmetologia',
        defaults={
            'name': 'Kosmetologia',
            'description': 'Zabiegi kosmetyczne i pielęgnacyjne',
            'order': 2,
            'is_active': True
        }
    )[0]
    
    cat_nails = ServiceCategory.objects.get_or_create(
        slug='manicure-pedicure',
        defaults={
            'name': 'Manicure & Pedicure',
            'description': 'Stylizacja i pielęgnacja paznokci',
            'order': 3,
            'is_active': True
        }
    )[0]
    
    cat_massage = ServiceCategory.objects.get_or_create(
        slug='masaze',
        defaults={
            'name': 'Masaże',
            'description': 'Masaże relaksacyjne i terapeutyczne',
            'order': 4,
            'is_active': True
        }
    )[0]
    
    print(f"✅ Utworzono {ServiceCategory.objects.count()} kategorii")
    
    # Usługi
    print("\n💇 Tworzenie usług...")
    
    services_data = [
        # Fryzjerstwo
        {
            'name': 'Strzyżenie damskie',
            'description_short': 'Profesjonalne strzyżenie z konsultacją stylisty',
            'description_full': '''Profesjonalne strzyżenie damskie z indywidualną konsultacją. 

W cenie:
• Analiza typu włosów i twarzy
• Mycie włosów profesjonalnymi kosmetykami
• Strzyżenie zgodne z najnowszymi trendami
• Stylizacja i suszenie
• Porady dotyczące pielęgnacji

Czas trwania: 30 minut
Idealne dla: Wszystkich typów włosów''',
            'duration_minutes': 30,
            'price': 80,
            'category': cat_hair,
            'color': '#FF6B9D',
            'icon': 'fa-cut',
            'is_active': True,
            'order': 1
        },
        {
            'name': 'Strzyżenie męskie',
            'description_short': 'Klasyczne lub nowoczesne cięcie dla mężczyzn',
            'description_full': '''Strzyżenie męskie dostosowane do stylu życia i preferencji.

W cenie:
• Konsultacja i dobór fryzury
• Mycie głowy
• Strzyżenie maszynką lub nożyczkami
• Modelowanie
• Golenie linii zarostu (opcjonalnie)

Czas trwania: 30 minut''',
            'duration_minutes': 30,
            'price': 60,
            'category': cat_hair,
            'color': '#4A90E2',
            'icon': 'fa-scissors',
            'is_active': True,
            'order': 2
        },
        {
            'name': 'Koloryzacja włosów',
            'description_short': 'Farbowanie, pasemka, baleyage - pełna koloryzacja',
            'description_full': '''Kompleksowa koloryzacja włosów najwyższej jakości kosmetykami.

Oferujemy:
• Farbowanie jednolite
• Pasemka (highlights)
• Baleyage i ombre
• Koloryzacja kreatywna
• Tonowanie i odświeżanie koloru

W cenie konsultacja kolorystyczna.
Czas trwania: 120 minut
Użyte produkty: Profesjonalne farby bez amoniaku''',
            'duration_minutes': 120,
            'price': 250,
            'category': cat_hair,
            'color': '#E94B3C',
            'icon': 'fa-palette',
            'is_active': True,
            'order': 3
        },
        
        # Kosmetologia
        {
            'name': 'Zabieg oczyszczający',
            'description_short': 'Głębokie oczyszczanie twarzy dla każdego typu cery',
            'description_full': '''Profesjonalny zabieg oczyszczający dostosowany do Twojej cery.

Etapy zabiegu:
• Demakijaż i oczyszczanie
• Peeling enzymatyczny
• Parownica i ekstrakcja zaskórników
• Maska oczyszczająca
• Tonizacja i nawilżanie
• Nakładanie kremu końcowego

Efekt: Czysta, gładka i odświeżona skóra
Czas trwania: 60 minut
Dla: Cery normalnej, mieszanej i tłustej''',
            'duration_minutes': 60,
            'price': 150,
            'category': cat_beauty,
            'color': '#50C878',
            'icon': 'fa-spa',
            'is_active': True,
            'order': 4
        },
        {
            'name': 'Mezoterapia igłowa',
            'description_short': 'Odżywczy zastrzyk witamin dla Twojej skóry',
            'description_full': '''Mezoterapia igłowa - skuteczna metoda odmładzania skóry.

Zalety zabiegu:
• Intensywne nawilżenie
• Poprawa elastyczności skóry
• Redukcja drobnych zmarszczek
• Wyrównanie kolorytu
• Poprawa owalu twarzy

Preparat: Koktajl witaminowy, kwas hialuronowy
Czas trwania: 45 minut
Zalecana seria: 3-5 zabiegów co 2 tygodnie''',
            'duration_minutes': 45,
            'price': 300,
            'category': cat_beauty,
            'color': '#9B59B6',
            'icon': 'fa-syringe',
            'is_active': True,
            'order': 5
        },
        
        # Manicure & Pedicure
        {
            'name': 'Manicure hybrydowy',
            'description_short': 'Trwały manicure hybrydowy utrzymujący się do 3 tygodni',
            'description_full': '''Manicure hybrydowy - piękne i zadbane paznokcie na długo.

W cenie:
• Przygotowanie płytki paznokcia
• Usunięcie skórek
• Pilowanie i nadanie kształtu
• Aplikacja bazy, koloru i topowego
• Utwardzanie w lampie UV/LED
• Olejek pielęgnacyjny

Trwałość: Do 3 tygodni
Czas trwania: 60 minut
Dostępne: Setki kolorów do wyboru''',
            'duration_minutes': 60,
            'price': 90,
            'category': cat_nails,
            'color': '#FF1493',
            'icon': 'fa-hand-sparkles',
            'is_active': True,
            'order': 6
        },
        {
            'name': 'Pedicure hybrydowy',
            'description_short': 'Kompleksowa pielęgnacja stóp z hybrydą',
            'description_full': '''Pedicure hybrydowy z pielęgnacją stóp.

Zakres zabiegu:
• Kąpiel stóp
• Usunięcie zrogowaceń
• Usunięcie skórek
• Pilowanie paznokci
• Lakier hybrydowy
• Masaż stóp z kremem nawilżającym

Efekt: Piękne i zadbane stopy
Czas trwania: 75 minut
Trwałość lakieru: Do 3 tygodni''',
            'duration_minutes': 75,
            'price': 120,
            'category': cat_nails,
            'color': '#FF69B4',
            'icon': 'fa-foot',
            'is_active': True,
            'order': 7
        },
        
        # Masaże
        {
            'name': 'Masaż relaksacyjny całego ciała',
            'description_short': 'Głęboko relaksujący masaż całego ciała',
            'description_full': '''Masaż relaksacyjny całego ciała dla odprężenia i regeneracji.

Techniki:
• Klasyczne ruchy masażu szwedzkiego
• Delikatne ugniatanie mięśni
• Aromaterapia (olejki eteryczne)
• Muzyka relaksacyjna
• Ciepłe ręczniki

Efekty:
• Głębokie odprężenie
• Redukcja stresu
• Poprawa krążenia
• Lepszy sen
• Ogólna regeneracja

Czas trwania: 90 minut
Idealne dla: Osób przepracowanych i zestresowanych''',
            'duration_minutes': 90,
            'price': 200,
            'category': cat_massage,
            'color': '#3498DB',
            'icon': 'fa-hands',
            'is_active': True,
            'order': 8
        },
        {
            'name': 'Masaż leczniczy kręgosłupa',
            'description_short': 'Terapeutyczny masaż na bóle pleców i karku',
            'description_full': '''Masaż leczniczy kręgosłupa dla ulgi w bólach pleców.

Wskazania:
• Bóle kręgosłupa
• Napięcie mięśni
• Siedzący tryb życia
• Stres i napięcia
• Ograniczona ruchomość

Techniki:
• Masaż głęboki tkanek
• Punkty spustowe (trigger points)
• Mobilizacje
• Rozciąganie

Czas trwania: 60 minut
Zalecana seria: 5-10 zabiegów''',
            'duration_minutes': 60,
            'price': 180,
            'category': cat_massage,
            'color': '#E67E22',
            'icon': 'fa-user-nurse',
            'is_active': True,
            'order': 9
        },
    ]
    
    created_services = []
    for service_data in services_data:
        service, created = Service.objects.get_or_create(
            name=service_data['name'],
            defaults=service_data
        )
        created_services.append(service)
        if created:
            print(f"  ✅ {service.name}")
        else:
            # Aktualizuj istniejące
            for key, value in service_data.items():
                setattr(service, key, value)
            service.save()
            print(f"  🔄 {service.name} (zaktualizowano)")
    
    print(f"\n✅ Utworzono/zaktualizowano {len(created_services)} usług")
    
    # Symulacja liczby rezerwacji dla "popularnych" usług
    print("\n📊 Symulowanie statystyk rezerwacji...")
    popular_services = [created_services[0], created_services[3], created_services[5]]
    for service in popular_services:
        service.booking_count = 25
        service.save()
        print(f"  ⭐ {service.name}: {service.booking_count} rezerwacji")
    
    print("\n" + "="*60)
    print("✨ KATALOG USŁUG ZOSTAŁ UTWORZONY! ✨")
    print("="*60)
    print(f"\n📊 Podsumowanie:")
    print(f"  • Kategorie: {ServiceCategory.objects.count()}")
    print(f"  • Usługi: {Service.objects.count()}")
    print(f"  • Aktywne usługi: {Service.objects.filter(is_active=True).count()}")
    print(f"\n🌐 Odwiedź katalog pod adresem: /uslugi/")
    print(f"🔧 Panel administracyjny: /admin/")
    print("\n💡 Wskazówka: Dodaj zdjęcia usług przez panel admina dla lepszej prezentacji!")

if __name__ == '__main__':
    create_catalog_data()
