from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Bus, Trip, BoardingLog
from django.utils import timezone
import datetime
from unittest.mock import patch

class TripScheduleTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Bus with specific schedule
        self.bus = Bus.objects.create(
            bus_number="BUS-01", 
            number_plate="KA01AB1234",
            morning_trip_end_time=datetime.time(12, 0, 0),
            evening_trip_start_time=datetime.time(12, 0, 0)
        )
        
        # Create Driver
        self.driver = User.objects.create_user(username='driver', password='password123', email='driver@test.com', is_driver=True)
        self.driver.bus = self.bus
        self.driver.save()
        
        # Create Student
        self.student = User.objects.create_user(username='student', password='password123', email='student@test.com', is_student=True)
        self.student.bus = self.bus
        self.student.save()
        
        self.start_trip_url = '/api/auth/trip/start/'
        self.boarding_url = '/api/auth/dashboard/student/board/'

    def test_start_morning_trip(self):
        self.client.force_authenticate(user=self.driver)
        
        # Mock time to 8:00 AM
        morning_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = morning_time
            mock_now.return_value = morning_time
            
            response = self.client.post(self.start_trip_url)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['trip_type'], 'morning')
            
            # Verify Trip created
            trip = Trip.objects.get(id=response.data['trip_id'])
            self.assertEqual(trip.trip_type, 'morning')

    def test_start_evening_trip(self):
        self.client.force_authenticate(user=self.driver)
        
        # Mock time to 4:00 PM (16:00)
        evening_time = timezone.now().replace(hour=16, minute=0, second=0, microsecond=0)
        
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = evening_time
            mock_now.return_value = evening_time
            
            response = self.client.post(self.start_trip_url)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['trip_type'], 'evening')

    def test_cannot_start_duplicate_trip(self):
        self.client.force_authenticate(user=self.driver)
        
        # Mock time to 8:00 AM
        morning_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = morning_time
            mock_now.return_value = morning_time
            
            # Start first trip
            self.client.post(self.start_trip_url)
            
            # Try to start second morning trip
            response = self.client.post(self.start_trip_url)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('already completed/started', response.data['error'])

    def test_boarding_linked_to_trip(self):
        self.client.force_authenticate(user=self.driver)
        
        # 1. Start Morning Trip
        morning_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = morning_time
            mock_now.return_value = morning_time
            self.client.post(self.start_trip_url)
            
            # Board Student
            boarding_data = {
                'qr_token': self.student.username, # Mocking token logic requires more setup, skipping token strict check in view if not implemented or mock bus verification
                # Wait, view uses timestamp signer for qr_token. Let's assume passed bus ID check or mock it.
                # Actually view expects qr_token to unsign to bus_id.
                # Let's bypass validation or mock signer? 
                # Easier to just create a valid token
            }
            from django.core.signing import TimestampSigner
            token = TimestampSigner().sign(self.bus.id)
            
            # Switch to Student
            self.client.force_authenticate(user=self.student)
            
            response = self.client.post(self.boarding_url, {
                'qr_token': token,
                'latitude': 12.34,
                'longitude': 56.78
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # Verify Log has trip
            log = BoardingLog.objects.first()
            self.assertEqual(log.trip.trip_type, 'morning')
            
            # Try boarding again same trip -> Fail
            response = self.client.post(self.boarding_url, {
                'qr_token': token,
                'latitude': 12.34,
                'longitude': 56.78
            })
            self.assertEqual(response.data['status'], 'already_boarded')

    def test_can_board_evening_trip_after_morning(self):
        self.client.force_authenticate(user=self.driver)
        
        # 1. Morning Flow
        morning_time = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = morning_time
            mock_now.return_value = morning_time
            self.client.post(self.start_trip_url)
            
            from django.core.signing import TimestampSigner
            token = TimestampSigner().sign(self.bus.id)
            
            # Switch to Student
            self.client.force_authenticate(user=self.student)
            self.client.post(self.boarding_url, {'qr_token': token, 'latitude': 12.34, 'longitude': 56.78})
            
        # 2. Evening Flow
        evening_time = timezone.now().replace(hour=16, minute=0, second=0, microsecond=0)
        with patch('django.utils.timezone.localtime') as mock_localtime, \
             patch('django.utils.timezone.now') as mock_now:
            mock_localtime.return_value = evening_time
            mock_now.return_value = evening_time
            
            # Start Evening Trip (Driver)
            self.client.force_authenticate(user=self.driver)
            self.client.post(self.start_trip_url)
            
            # Board Same Student (Student)
            self.client.force_authenticate(user=self.student)
            response = self.client.post(self.boarding_url, {
                'qr_token': token,
                'latitude': 12.34,
                'longitude': 56.78
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['message'], 'Boarding successful!')

            # Verify 2 logs exist
            self.assertEqual(BoardingLog.objects.count(), 2)
