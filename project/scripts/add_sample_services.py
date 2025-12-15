#!/usr/bin/env python
"""Add sample services for testing booking system"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from ideas.models import Service

# Create sample services
services_data = [
    {
        'name': 'Manicure klasyczny',
        'description': 'Klasyczny manicure z pielęgnacją skórek i lakierowaniem',
        'duration_minutes': 45,
        'price': 60.00
    },
    {
        'name': 'Manicure hybrydowy',
        'description': 'Manicure hybrydowy z lakierem hybrydowym - trwałość do 3 tygodni',
        'duration_minutes': 60,
        'price': 80.00
    },
    {
        'name': 'Pedicure klasyczny',
        'description': 'Profesjonalny pedicure z pielęgnacją stóp',
        'duration_minutes': 60,
        'price': 70.00
    },
    {
        'name': 'Paznokcie żelowe',
        'description': 'Przedłużanie paznokci żelem - naturalne lub z tipem',
        'duration_minutes': 90,
        'price': 120.00
    },
    {
        'name': 'Zdobienie paznokci',
        'description': 'Artystyczne zdobienie paznokci - wzory, kryształki, efekty',
        'duration_minutes': 30,
        'price': 40.00
    },
]

print("Dodawanie przykładowych usług...")
created_count = 0
updated_count = 0

for service_data in services_data:
    service, created = Service.objects.get_or_create(
        name=service_data['name'],
        defaults=service_data
    )
    if created:
        created_count += 1
        print(f"✓ Utworzono: {service.name} ({service.duration_minutes} min, {service.price} PLN)")
    else:
        updated_count += 1
        print(f"⚠ Już istnieje: {service.name}")

print(f"\nPodsumowanie:")
print(f"- Nowe usługi: {created_count}")
print(f"- Istniejące: {updated_count}")
print(f"- Razem w bazie: {Service.objects.count()}")
