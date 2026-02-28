from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.core.signing import TimestampSigner
from .models import Bus
import time

User = get_user_model()

class DynamicQRTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.management_user = User.objects.create_user(username='manager', password='password', is_management=True)
        self.driver_user = User.objects.create_user(username='driver', password='password', is_driver=True, managed_by=self.management_user)
        self.student_user = User.objects.create_user(username='student', password='password', is_student=True, managed_by=self.management_user)
        self.bus = Bus.objects.create(bus_number='BUS-001', number_plate='XYZ-123', management=self.management_user)
        self.driver_user.bus = self.bus
        self.driver_user.save()
        
        # Authenticate driver to get token
        self.client.force_authenticate(user=self.driver_user)

    def test_generate_qr_token(self):
        """Test that the driver dashboard returns a signed QR token"""
        url = reverse('driver_dashboard_stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('qr_token', response.data)
        
        qr_token = response.data['qr_token']
        signer = TimestampSigner()
        bus_id = signer.unsign(qr_token)
        self.assertEqual(int(bus_id), self.bus.id)

    def test_verify_qr_token_success(self):
        """Test that a valid QR token allows boarding"""
        # Generate token
        signer = TimestampSigner()
        qr_token = signer.sign(self.bus.id)
        
        # Authenticate as student
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('student_board')
        data = {
            'qr_token': qr_token,
            'latitude': 10.0,
            'longitude': 20.0
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['bus'], self.bus.bus_number)

    def test_verify_qr_token_expired(self):
        """Test that an expired QR token is rejected"""
        # Generate token with a very short max_age in the past?
        # Since unsign takes max_age, we can just sleep or mock timestamp.
        # But we can't easily mock timestamp in integration test without patching.
        # Instead, let's use a token generated a while ago.
        
        signer = TimestampSigner()
        # Create a token that appears to be old.
        # TimestampSigner uses time.time(). We can manually construct an old token or patch time.
        
        from django.core.signing import b62_encode
        
        # Manually create an old token
        # format: value:timestamp:signature
        # timestamp is base62 encoded int(time.time())
        
        old_time = int(time.time()) - 40 # 40 seconds ago
        value = str(self.bus.id)
        timestamp = b62_encode(old_time)
        value_to_sign = f'{value}:{timestamp}'
        signature = signer.signature(value_to_sign)
        expired_token = f'{value_to_sign}:{signature}'
        
        # Authenticate as student
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('student_board')
        data = {
            'qr_token': expired_token,
            'latitude': 10.0,
            'longitude': 20.0
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'].lower())

    def test_verify_qr_token_invalid(self):
        """Test that a tampered QR token is rejected"""
        signer = TimestampSigner()
        qr_token = signer.sign(self.bus.id)
        
        # Tamper with the token
        tampered_token = qr_token + 'junk'
        
        # Authenticate as student
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('student_board')
        data = {
            'qr_token': tampered_token,
            'latitude': 10.0,
            'longitude': 20.0
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invalid', response.data['error'].lower())
