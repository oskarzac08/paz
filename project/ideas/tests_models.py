"""
Testy jednostkowe dla modeli aplikacji ideas
"""
import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from ideas.models import (
    Service, ServiceCategory, ServiceImage,
    Reservation, TimeSlot, UserProfile
)


@pytest.mark.django_db
class TestServiceCategory:
    """Testy dla modelu ServiceCategory"""
    
    def test_create_category(self):
        """Test tworzenia kategorii usług"""
        category = ServiceCategory.objects.create(
            name="Manicure",
            slug="manicure",
            description="Usługi manicure",
            is_active=True,
            order=1
        )
        assert category.name == "Manicure"
        assert category.slug == "manicure"
        assert category.is_active is True
        assert str(category) == "Manicure"
    
    def test_category_ordering(self):
        """Test sortowania kategorii według pola order"""
        # Usuń istniejące kategorie z testowej bazy
        ServiceCategory.objects.all().delete()
        
        cat1 = ServiceCategory.objects.create(name="Cat1", slug="cat1", order=2)
        cat2 = ServiceCategory.objects.create(name="Cat2", slug="cat2", order=1)
        cat3 = ServiceCategory.objects.create(name="Cat3", slug="cat3", order=3)
        
        categories = list(ServiceCategory.objects.all())
        assert categories[0] == cat2  # order=1
        assert categories[1] == cat1  # order=2
        assert categories[2] == cat3  # order=3
    
    def test_unique_slug(self):
        """Test unikalności slug"""
        ServiceCategory.objects.create(name="Cat1", slug="test-slug")
        
        with pytest.raises(Exception):  # IntegrityError
            ServiceCategory.objects.create(name="Cat2", slug="test-slug")


@pytest.mark.django_db
class TestService:
    """Testy dla modelu Service"""
    
    @pytest.fixture
    def category(self):
        """Fixture - kategoria testowa"""
        return ServiceCategory.objects.create(
            name="Test Category",
            slug="test-category"
        )
    
    def test_create_service(self, category):
        """Test tworzenia usługi"""
        service = Service.objects.create(
            name="Manicure klasyczny",
            category=category,
            price=Decimal("100.00"),
            duration_minutes=45,
            is_active=True
        )
        assert service.name == "Manicure klasyczny"
        assert service.price == Decimal("100.00")
        assert service.duration_minutes == 45
        assert str(service) == "Manicure klasyczny"
    
    def test_duration_validation_negative(self, category):
        """Test walidacji - czas trwania nie może być ujemny"""
        service = Service(
            name="Test Service",
            category=category,
            price=Decimal("100.00"),
            duration_minutes=-30
        )
        
        with pytest.raises(ValidationError):
            service.full_clean()
    
    def test_color_and_icon(self, category):
        """Test pól color i icon"""
        service = Service.objects.create(
            name="Przedłużanie paznokci",
            category=category,
            price=Decimal("200.00"),
            duration_minutes=90,
            color="#FF5733",
            icon="fa-cut"
        )
        assert service.color == "#FF5733"
        assert service.icon == "fa-cut"
    
    def test_booking_count_increment(self, category):
        """Test inkrementacji licznika rezerwacji"""
        service = Service.objects.create(
            name="Test",
            category=category,
            price=Decimal("100.00"),
            duration_minutes=30,
            booking_count=5
        )
        service.booking_count += 1
        service.save()
        
        service.refresh_from_db()
        assert service.booking_count == 6


@pytest.mark.django_db
class TestTimeSlot:
    """Testy dla modelu TimeSlot"""
    
    @pytest.fixture
    def service(self):
        """Fixture - usługa testowa"""
        category = ServiceCategory.objects.create(name="Test", slug="test")
        return Service.objects.create(
            name="Test Service",
            category=category,
            price=Decimal("100.00"),
            duration_minutes=60
        )
    
    def test_create_timeslot(self, service):
        """Test tworzenia slotu czasowego"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        slot = TimeSlot.objects.create(
            service=service,
            start=start_time,
            end=end_time,
            status='available'
        )
        
        assert slot.service == service
        assert slot.is_available is True
        assert slot.end > slot.start
    
    def test_timeslot_ordering(self, service):
        """Test sortowania slotów według czasu"""
        now = timezone.now()
        slot1 = TimeSlot.objects.create(
            service=service,
            start=now + timedelta(hours=2),
            end=now + timedelta(hours=3),
            status='available'
        )
        slot2 = TimeSlot.objects.create(
            service=service,
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            status='available'
        )
        
        slots = list(TimeSlot.objects.all())
        assert slots[0] == slot2  # wcześniejszy
        assert slots[1] == slot1  # późniejszy


@pytest.mark.django_db
class TestReservation:
    """Testy dla modelu Reservation"""
    
    @pytest.fixture
    def user(self):
        """Fixture - użytkownik testowy"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def service(self):
        """Fixture - usługa testowa"""
        category = ServiceCategory.objects.create(name="Test", slug="test")
        return Service.objects.create(
            name="Test Service",
            category=category,
            price=Decimal("150.00"),
            duration_minutes=60
        )
    
    @pytest.fixture
    def timeslot(self, service):
        """Fixture - slot czasowy"""
        start = timezone.now() + timedelta(days=1)
        return TimeSlot.objects.create(
            service=service,
            start=start,
            end=start + timedelta(hours=1),
            status='available'
        )
    
    def test_create_reservation(self, user, service, timeslot):
        """Test tworzenia rezerwacji"""
        reservation = Reservation.objects.create(
            user=user,
            service=service,
            timeslot=timeslot,
            start=timeslot.start,
            end=timeslot.end,
            customer_email=user.email,
            status='pending'
        )
        
        assert reservation.user == user
        assert reservation.service == service
        assert reservation.status == 'pending'
    
    def test_reservation_status_choices(self, user, service, timeslot):
        """Test dostępnych statusów rezerwacji"""
        valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        
        for status in valid_statuses:
            reservation = Reservation.objects.create(
                user=user,
                service=service,
                timeslot=timeslot,
                start=timeslot.start,
                end=timeslot.end,
                customer_email=user.email,
                status=status
            )
            assert reservation.status == status
            reservation.delete()
    
    def test_reservation_cancellation(self, user, service, timeslot):
        """Test anulowania rezerwacji"""
        reservation = Reservation.objects.create(
            user=user,
            service=service,
            timeslot=timeslot,
            start=timeslot.start,
            end=timeslot.end,
            customer_email=user.email,
            status='confirmed'
        )
        
        # Anulowanie
        reservation.status = 'cancelled'
        reservation.cancelled_at = timezone.now()
        reservation.save()
        
        reservation.refresh_from_db()
        assert reservation.status == 'cancelled'
        assert reservation.cancelled_at is not None


@pytest.mark.django_db
class TestUserProfile:
    """Testy dla modelu UserProfile"""
    
    def test_create_user_profile(self):
        """Test tworzenia profilu użytkownika"""
        user = User.objects.create_user(
            username='profile_test_user',
            email='profiletest@example.com'
        )
        
        # Profil jest tworzony automatycznie przez signal
        profile = user.profile
        profile.phone_number = '+48123456789'
        profile.preferred_contact = 'email'
        profile.email_verified = False
        profile.phone_verified = False
        profile.save()
        
        assert profile.user == user
        assert profile.phone_number == '+48123456789'
        assert profile.preferred_contact == 'email'
        assert profile.is_verified is False  # property sprawdzające email_verified or phone_verified
    
    def test_phone_number_validation(self):
        """Test walidacji numeru telefonu"""
        user = User.objects.create_user(username='phone_test_user', email='phonetest@test.com')
        
        # Profil automatycznie utworzony przez signal
        profile = user.profile
        profile.phone_number = '+48123456789'
        profile.save()
        assert profile.phone_number == '+48123456789'
    
    def test_preferred_contact_choices(self):
        """Test wyboru preferowanego kontaktu"""
        user = User.objects.create_user(username='contact_test_user', email='contacttest@test.com')
        
        # Profil automatycznie utworzony przez signal
        profile = user.profile
        profile.preferred_contact = 'email'
        profile.save()
        assert profile.preferred_contact == 'email'
        
        # SMS
        profile.preferred_contact = 'sms'
        profile.save()
        profile.refresh_from_db()
        assert profile.preferred_contact == 'sms'


@pytest.mark.django_db
class TestServiceImage:
    """Testy dla modelu ServiceImage"""
    
    @pytest.fixture
    def service(self):
        """Fixture - usługa testowa"""
        category = ServiceCategory.objects.create(name="Test", slug="test")
        return Service.objects.create(
            name="Test Service",
            category=category,
            price=Decimal("100.00"),
            duration_minutes=60
        )
    
    def test_primary_image_flag(self, service):
        """Test flagi is_primary"""
        image1 = ServiceImage.objects.create(
            service=service,
            image='test1.jpg',
            is_primary=True,
            order=1
        )
        
        image2 = ServiceImage.objects.create(
            service=service,
            image='test2.jpg',
            is_primary=False,
            order=2
        )
        
        assert image1.is_primary is True
        assert image2.is_primary is False
        assert service.primary_image == image1
    
    def test_image_ordering(self, service):
        """Test sortowania obrazów według order"""
        img3 = ServiceImage.objects.create(
            service=service, image='3.jpg', order=3
        )
        img1 = ServiceImage.objects.create(
            service=service, image='1.jpg', order=1
        )
        img2 = ServiceImage.objects.create(
            service=service, image='2.jpg', order=2
        )
        
        images = list(service.images.all())
        assert images[0] == img1
        assert images[1] == img2
        assert images[2] == img3
