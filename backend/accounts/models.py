from django.contrib.auth.models import AbstractUser
from django.db import models

class Bus(models.Model):
    bus_number = models.CharField(max_length=20)
    destination = models.CharField(max_length=100, blank=True, null=True)
    number_plate = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to='bus_photos/', blank=True, null=True)
    
    # Real-time Location
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_update = models.DateTimeField(null=True, blank=True)
    
    # Link to management user who owns/manages this bus
    management = models.ForeignKey('User', on_delete=models.CASCADE, related_name='buses', null=True, blank=True)

    # Trip Restrictions
    morning_trip_end_time = models.TimeField(default='12:00:00') # Trips before this are "Morning"
    evening_trip_start_time = models.TimeField(default='12:00:00') # Trips after this are "Evening"

    def __str__(self):
        return f"{self.bus_number}"

class Grade(models.Model):
    name = models.CharField(max_length=20) # e.g. "10", "1", "Kindergarten"
    section = models.CharField(max_length=5) # e.g. "A", "B"

    class Meta:
        unique_together = ('name', 'section')

    def __str__(self):
        return f"{self.name} - {self.section}"

class User(AbstractUser):
    is_parent = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)
    is_management = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)

    phone = models.CharField(max_length=20, blank=True, null=True)
    organization_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Global Trip Schedule for Organization (Management User)
    morning_arrival_time = models.TimeField(default='09:00:00', help_text="Time by which buses should arrive at college")
    evening_departure_time = models.TimeField(default='16:00:00', help_text="Time from which buses depart from college")
    
    # Push Notification Token
    push_token = models.CharField(max_length=255, blank=True, null=True)
    
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    managed_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='managed_members')
    
    # Teacher specific fields
    class_in_charge = models.ForeignKey(Grade, null=True, blank=True, on_delete=models.SET_NULL, related_name='class_teacher')
    bus = models.ForeignKey(Bus, null=True, blank=True, on_delete=models.SET_NULL, related_name='passengers')

    def __str__(self):
        return self.username

class PasswordResetOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        from django.utils import timezone
        import datetime
        # OTP valid for 10 minutes
        return self.created_at >= timezone.now() - datetime.timedelta(minutes=10)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=[
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success')
    ], default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

class Trip(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='trips')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    trip_type = models.CharField(max_length=20, choices=[('morning', 'Morning'), ('evening', 'Evening')], default='morning')
    
    def __str__(self):
        return f"Trip {self.id} - {self.bus.bus_number} ({self.trip_type})"

class BoardingLog(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boarding_logs')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='boarding_logs')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='boarding_logs', null=True, blank=True)
    scan_time = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'trip') # Student can board only once per trip

    def __str__(self):
        return f"{self.student.username} boarded {self.bus.bus_number} at {self.scan_time}"

class Complaint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=[
        ('submitted', 'Submitted'),
        ('in_action', 'In Action'),
        ('resolved', 'Resolved')
    ], default='submitted')
    administrative_response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"
