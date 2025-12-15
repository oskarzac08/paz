from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Service, Reservation
import datetime

class BookingFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.service = Service.objects.create(name='Test Service', duration_minutes=30, price=100)

    def test_service_selection_and_datetime(self):
        # Step 1: select service
        res = self.client.post(reverse('ideas:booking_service'), {'service': self.service.id})
        self.assertEqual(res.status_code, 302)
        # follow to datetime
        res = self.client.get(reverse('ideas:booking_datetime'))
        self.assertEqual(res.status_code, 200)

    def test_booking_create(self):
        session = self.client.session
        session['booking_service_id'] = self.service.id
        session.save()
        # pick tomorrow at 10:00
        tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
        res = self.client.post(reverse('ideas:booking_datetime'), {'date': tomorrow.isoformat(), 'time': '10:00'})
        self.assertIn('booking_start', self.client.session)
        # go to summary and confirm
        res = self.client.post(reverse('ideas:booking_summary'), {'accept_terms': True})
        self.assertEqual(res.status_code, 302)
        self.assertIn('booking_reservation_id', self.client.session)
        rid = self.client.session['booking_reservation_id']
        self.assertTrue(Reservation.objects.filter(id=rid).exists())
