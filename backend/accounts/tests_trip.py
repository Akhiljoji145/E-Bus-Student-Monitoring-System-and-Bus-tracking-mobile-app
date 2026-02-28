from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Bus, Grade, Trip
from django.urls import reverse

class BusLocationAccessTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Bus
        self.bus = Bus.objects.create(bus_number="BUS-01", number_plate="KA01AB1234")
        self.other_bus = Bus.objects.create(bus_number="BUS-02", number_plate="KA02CD5678")
        
        # Create Management User
        self.management_user = User.objects.create_user(username='management', password='password123', is_management=True)
        self.bus.management = self.management_user
        self.bus.save()
        
        # Create Driver
        self.driver = User.objects.create_user(username='driver', password='password123', is_driver=True)
        self.driver.bus = self.bus
        self.driver.save()
        
        # Create Student assigned to Bus 1
        self.student = User.objects.create_user(username='student', password='password123', is_student=True)
        self.student.bus = self.bus
        self.student.save()
        
        # Create Student assigned to Bus 2
        self.other_student = User.objects.create_user(username='other_student', password='password123', is_student=True)
        self.other_student.bus = self.other_bus
        self.other_student.save()
        
        # Create Parent with child in Bus 1
        self.parent = User.objects.create_user(username='parent', password='password123', is_parent=True)
        self.student.parent = self.parent
        self.student.save()
        
        # Create Parent with NO child in Bus 1
        self.other_parent = User.objects.create_user(username='other_parent', password='password123', is_parent=True)
        
        self.url = reverse('bus_location', args=[self.bus.id])

    def test_student_can_track_own_bus(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_track_other_bus(self):
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_parent_can_track_child_bus(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_parent_cannot_track_other_bus(self):
        self.client.force_authenticate(user=self.other_parent)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_can_track_own_bus(self):
        self.client.force_authenticate(user=self.driver)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_management_can_track_managed_bus(self):
        self.client.force_authenticate(user=self.management_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
