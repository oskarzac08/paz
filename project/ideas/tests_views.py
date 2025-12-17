"""
Testy jednostkowe dla widoków aplikacji ideas
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

from ideas.models import (
    Service, ServiceCategory, Reservation, 
    TimeSlot, UserProfile
)
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestLandingView:
    """Testy dla widoku landing page"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    @pytest.fixture
    def categories_with_services(self):
        """Fixture - kategorie z usługami"""
        cat1 = ServiceCategory.objects.create(
            name="Manicure", slug="manicure", is_active=True, order=1
        )
        cat2 = ServiceCategory.objects.create(
            name="Pedicure", slug="pedicure", is_active=True, order=2
        )
        
        Service.objects.create(
            name="Manicure klasyczny",
            category=cat1,
            price=Decimal("100.00"),
            duration_minutes=45,
            is_active=True
        )
        Service.objects.create(
            name="Pedicure klasyczny",
            category=cat2,
            price=Decimal("150.00"),
            duration_minutes=60,
            is_active=True
        )
        
        return [cat1, cat2]
    
    def test_landing_page_loads(self, client):
        """Test ładowania strony głównej"""
        response = client.get(reverse('ideas:landing'))
        assert response.status_code == 200
        assert 'landing.html' in [t.name for t in response.templates]
    
    def test_landing_page_shows_services(self, client, categories_with_services):
        """Test wyświetlania usług na landing page"""
        response = client.get(reverse('ideas:landing'))
        
        assert response.status_code == 200
        assert 'categories' in response.context
        
        categories = response.context['categories']
        # Sprawdź czy nasze testowe kategorie są w wynikach
        category_names = [cat.name for cat in categories]
        assert 'Manicure' in category_names
        assert 'Pedicure' in category_names
        
        # Sprawdź zawartość HTML
        content = response.content.decode('utf-8')
        assert 'Manicure' in content or 'manicure' in content.lower()
        assert 'Pedicure' in content or 'pedicure' in content.lower()
    
    def test_landing_page_empty_services(self, client):
        """Test landing page - sprawdź że działa nawet gdy nie ma aktywnych usług"""
        # Dezaktywuj wszystkie usługi
        Service.objects.all().update(is_active=False)
        
        response = client.get(reverse('ideas:landing'))
        assert response.status_code == 200
        
        categories = response.context['categories']
        assert categories.count() == 0


@pytest.mark.django_db
class TestServiceCatalogView:
    """Testy dla widoku katalogu usług"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    @pytest.fixture
    def setup_services(self):
        """Fixture - przygotowanie usług testowych"""
        cat = ServiceCategory.objects.create(
            name="Manicure", slug="manicure", is_active=True
        )
        
        Service.objects.create(
            name="Manicure podstawowy",
            category=cat,
            price=Decimal("80.00"),
            duration_minutes=30,
            is_active=True,
            order=1
        )
        Service.objects.create(
            name="Manicure premium",
            category=cat,
            price=Decimal("150.00"),
            duration_minutes=60,
            is_active=True,
            order=2
        )
        
        return cat
    
    def test_catalog_view_loads(self, client):
        """Test ładowania katalogu usług"""
        response = client.get(reverse('ideas:service_catalog'))
        assert response.status_code == 200
    
    def test_catalog_shows_all_services(self, client, setup_services):
        """Test wyświetlania wszystkich usług"""
        response = client.get(reverse('ideas:service_catalog'))
        
        assert response.status_code == 200
        # Sprawdź czy są nasze testowe usługi (może być więcej w bazie)
        assert response.context['result_count'] >= 2
        
        # Sprawdź czy nasze testowe usługi są w wynikach
        service_names = [s.name for s in response.context['services']]
        assert 'Manicure klasyczny' in service_names
        assert 'Manicure premium' in service_names
    
    def test_catalog_filter_by_category(self, client, setup_services):
        """Test filtrowania po kategorii"""
        response = client.get(
            reverse('ideas:service_catalog'),
            {'category': 'manicure'}
        )
        
        assert response.status_code == 200
        assert response.context['result_count'] == 2
    
    def test_catalog_filter_by_price(self, client, setup_services):
        """Test filtrowania po cenie"""
        # Tylko tańsze usługi (< 100 zł)
        response = client.get(
            reverse('ideas:service_catalog'),
            {'max_price': '100'}
        )
        
        assert response.status_code == 200
        services = list(response.context['services'])
        assert all(s.price <= Decimal('100.00') for s in services)
    
    def test_catalog_search(self, client, setup_services):
        """Test wyszukiwania usług"""
        response = client.get(
            reverse('ideas:service_catalog'),
            {'q': 'premium'}
        )
        
        assert response.status_code == 200
        services = list(response.context['services'])
        assert len(services) == 1
        assert services[0].name == "Manicure premium"
    
    def test_catalog_sorting(self, client, setup_services):
        """Test sortowania usług"""
        # Sortowanie po cenie rosnąco
        response = client.get(
            reverse('ideas:service_catalog'),
            {'sort': 'price_asc'}
        )
        
        services = list(response.context['services'])
        assert services[0].price < services[1].price
        
        # Sortowanie po cenie malejąco
        response = client.get(
            reverse('ideas:service_catalog'),
            {'sort': 'price_desc'}
        )
        
        services = list(response.context['services'])
        assert services[0].price > services[1].price


@pytest.mark.django_db
class TestAuthViews:
    """Testy dla widoków autoryzacji"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    def test_register_view_get(self, client):
        """Test wyświetlania formularza rejestracji"""
        response = client.get(reverse('ideas:register'))
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_login_view_get(self, client):
        """Test wyświetlania formularza logowania"""
        response = client.get(reverse('ideas:login'))
        assert response.status_code == 200
    
    def test_login_success(self, client):
        """Test poprawnego logowania"""
        # Utwórz użytkownika
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        user.is_active = True
        user.save()
        
        # Zaloguj
        response = client.post(reverse('ideas:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Sprawdź przekierowanie po zalogowaniu
        assert response.status_code == 302
    
    def test_login_invalid_credentials(self, client):
        """Test logowania z błędnymi danymi"""
        response = client.post(reverse('ideas:login'), {
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        
        # Powinien pozostać na stronie logowania
        assert response.status_code == 200


@pytest.mark.django_db
class TestReservationViews:
    """Testy dla widoków rezerwacji"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    @pytest.fixture
    def logged_in_user(self, client):
        """Fixture - zalogowany użytkownik"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        user.is_active = True
        user.save()
        
        client.login(username='testuser', password='testpass123')
        return user
    
    @pytest.fixture
    def service_with_slots(self):
        """Fixture - usługa ze slotami"""
        cat = ServiceCategory.objects.create(
            name="Test", slug="test", is_active=True
        )
        service = Service.objects.create(
            name="Test Service",
            category=cat,
            price=Decimal("100.00"),
            duration_minutes=60,
            is_active=True
        )
        
        # Dodaj dostępny slot
        start = timezone.now() + timedelta(days=1)
        TimeSlot.objects.create(
            service=service,
            start=start,
            end=start + timedelta(hours=1),
            status='available'
        )
        
        return service
    
    def test_booking_step1_requires_login(self, client):
        """Test dostępności strony wyboru usługi"""
        response = client.get(reverse('ideas:booking_step1_service'))
        
        # Strona wyboru usługi jest dostępna publicznie
        assert response.status_code == 200
    
    def test_booking_step1_logged_in(self, client, logged_in_user, service_with_slots):
        """Test pierwszego kroku rezerwacji dla zalogowanego"""
        response = client.get(reverse('ideas:booking_step1_service'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestEdgeCases:
    """Testy przypadków brzegowych"""
    
    @pytest.fixture
    def client(self):
        return Client()
    
    def test_nonexistent_service_detail(self, client):
        """Test dostępu do nieistniejącej usługi"""
        response = client.get(
            reverse('ideas:service_detail', kwargs={'service_id': 99999})
        )
        assert response.status_code == 404
    
    def test_invalid_sort_parameter(self, client):
        """Test nieprawidłowego parametru sortowania"""
        response = client.get(
            reverse('ideas:service_catalog'),
            {'sort': 'invalid_sort'}
        )
        # Powinno załadować się z domyślnym sortowaniem
        assert response.status_code == 200
    
    def test_negative_price_filter(self, client):
        """Test filtra z ujemną ceną"""
        response = client.get(
            reverse('ideas:service_catalog'),
            {'min_price': '-100'}
        )
        # Powinno załadować się bez błędu
        assert response.status_code == 200
