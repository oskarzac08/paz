"""
Testy dla systemu odwoływania wizyt
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core import mail
from datetime import timedelta
from ideas.models import Service, Reservation


class ReservationCancellationModelTests(TestCase):
    """Testy modelu Reservation - funkcjonalność odwoływania"""
    
    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        self.service = Service.objects.create(
            name='Test Service',
            description='Test Description',
            duration_minutes=60,
            price=100.00
        )
    
    def test_can_cancel_future_reservation_by_customer(self):
        """Test: Klient może odwołać wizytę >24h przed terminem"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            customer_first_name='Jan',
            customer_last_name='Kowalski',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        can_cancel, message = reservation.can_cancel(by_staff=False)
        self.assertTrue(can_cancel)
        self.assertEqual(message, "")
    
    def test_cannot_cancel_less_than_24h_by_customer(self):
        """Test: Klient nie może odwołać wizyty <24h przed terminem"""
        near_start = timezone.now() + timedelta(hours=12)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=near_start,
            end=near_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        can_cancel, message = reservation.can_cancel(by_staff=False)
        self.assertFalse(can_cancel)
        self.assertIn("Za późno", message)
    
    def test_staff_can_cancel_anytime(self):
        """Test: Obsługa może odwołać wizytę w każdym momencie"""
        near_start = timezone.now() + timedelta(hours=1)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=near_start,
            end=near_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        can_cancel, message = reservation.can_cancel(by_staff=True)
        self.assertTrue(can_cancel)
    
    def test_cancel_reservation_changes_status(self):
        """Test: Odwołanie wizyty zmienia status na 'cancelled'"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        reservation.cancel(
            cancelled_by=self.user,
            by_staff=False,
            reason='change_plans',
            note='Test cancellation'
        )
        
        self.assertEqual(reservation.status, 'cancelled')
        self.assertIsNotNone(reservation.cancelled_at)
        self.assertEqual(reservation.cancelled_by, self.user)
        self.assertFalse(reservation.cancelled_by_staff)
        self.assertEqual(reservation.cancellation_reason, 'change_plans')
    
    def test_cannot_cancel_already_cancelled(self):
        """Test: Nie można odwołać już odwołanej wizyty"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='cancelled'
        )
        
        can_cancel, message = reservation.can_cancel(by_staff=False)
        self.assertFalse(can_cancel)
        self.assertIn("odwołana", message.lower())
    
    def test_generate_cancellation_token(self):
        """Test: Generowanie tokena odwołania"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        token = reservation.generate_cancellation_token()
        
        self.assertIsNotNone(token)
        self.assertEqual(reservation.cancellation_token, token)
        self.assertIsNotNone(reservation.cancellation_token_expires)
        
        # Token powinien wygasać za około 7 dni (6-7 dni)
        expires_diff = (reservation.cancellation_token_expires - timezone.now()).days
        self.assertIn(expires_diff, [6, 7])  # Może być 6 lub 7 w zależności od godziny


class CancellationViewsTests(TestCase):
    """Testy widoków odwoływania wizyt"""
    
    def setUp(self):
        """Przygotowanie danych testowych"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = Service.objects.create(
            name='Test Service',
            duration_minutes=60,
            price=100.00
        )
    
    def test_my_reservations_requires_login(self):
        """Test: Widok 'moje wizyty' wymaga logowania"""
        response = self.client.get('/moje-wizyty/')
        self.assertEqual(response.status_code, 302)  # Redirect do logowania
    
    def test_my_reservations_shows_upcoming(self):
        """Test: Widok pokazuje nadchodzące wizyty"""
        self.client.login(username='testuser', password='testpass123')
        
        future_start = timezone.now() + timedelta(days=3)
        Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        response = self.client.get('/moje-wizyty/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Service')
    
    def test_cancel_reservation_view_requires_login(self):
        """Test: Odwoływanie wizyty wymaga logowania"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        response = self.client.get(f'/odwolaj/{reservation.id}/')
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_cancel_reservation_successful(self):
        """Test: Pomyślne odwołanie wizyty"""
        self.client.login(username='testuser', password='testpass123')
        
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        response = self.client.post(f'/odwolaj/{reservation.id}/', {
            'reason': 'change_plans',
            'note': 'Test note'
        })
        
        # Powinno przekierować do strony sukcesu
        self.assertEqual(response.status_code, 302)
        
        # Sprawdź czy wizyta została odwołana
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')
        self.assertEqual(reservation.cancellation_reason, 'change_plans')
    
    def test_cancel_with_token_no_login(self):
        """Test: Odwołanie z tokenem bez logowania"""
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        token = reservation.generate_cancellation_token()
        
        response = self.client.get(f'/odwolaj/token/{token}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Service')
    
    def test_cancel_with_invalid_token(self):
        """Test: Odwołanie z nieprawidłowym tokenem"""
        response = self.client.get('/odwolaj/token/invalid-token-123/')
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_cancellation_sends_email(self):
        """Test: Odwołanie wysyła e-mail"""
        self.client.login(username='testuser', password='testpass123')
        
        future_start = timezone.now() + timedelta(days=3)
        reservation = Reservation.objects.create(
            service=self.service,
            user=self.user,
            customer_email='test@example.com',
            start=future_start,
            end=future_start + timedelta(minutes=60),
            status='confirmed'
        )
        
        self.client.post(f'/odwolaj/{reservation.id}/', {
            'reason': 'illness',
            'note': ''
        })
        
        # Sprawdź czy e-mail został wysłany (do klienta, może do obsługi jeśli są staff users)
        self.assertGreaterEqual(len(mail.outbox), 1)  # Minimum do klienta


class CancellationStatisticsTests(TestCase):
    """Testy statystyk odwoływania"""
    
    def setUp(self):
        """Przygotowanie danych testowych"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = Service.objects.create(
            name='Test Service',
            duration_minutes=60,
            price=100.00
        )
    
    def test_cancellation_rate_calculation(self):
        """Test: Obliczanie wskaźnika odwołań"""
        # Utwórz 10 wizyt
        for i in range(10):
            start = timezone.now() - timedelta(days=i+1)
            status = 'cancelled' if i < 3 else 'completed'
            Reservation.objects.create(
                service=self.service,
                user=self.user,
                customer_email='test@example.com',
                start=start,
                end=start + timedelta(minutes=60),
                status=status
            )
        
        total = Reservation.objects.filter(user=self.user).count()
        cancelled = Reservation.objects.filter(
            user=self.user, 
            status='cancelled'
        ).count()
        
        self.assertEqual(total, 10)
        self.assertEqual(cancelled, 3)
        
        rate = (cancelled / total * 100)
        self.assertEqual(rate, 30.0)
