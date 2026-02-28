from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class ChildSerializer(serializers.ModelSerializer):
    bus_id = serializers.PrimaryKeyRelatedField(source='bus', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'bus_id']

class UserSerializer(serializers.ModelSerializer):
    bus_id = serializers.PrimaryKeyRelatedField(source='bus', read_only=True)
    children = ChildSerializer(many=True, read_only=True)
    resolved_organization_name = serializers.SerializerMethodField()
    class_in_charge_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'is_superuser', 'is_staff', 'is_parent', 'is_teacher', 'is_driver', 'is_management', 'is_student', 'bus_id', 'children', 'morning_arrival_time', 'evening_departure_time', 'push_token', 'resolved_organization_name', 'class_in_charge_name']

    def get_resolved_organization_name(self, obj):
        if obj.organization_name:
            return obj.organization_name
        if obj.managed_by and obj.managed_by.organization_name:
            return obj.managed_by.organization_name
        return "EduTransit College"

    def get_class_in_charge_name(self, obj):
        if obj.class_in_charge:
            return str(obj.class_in_charge)
        return "Not Assigned"

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['is_superuser'] = user.is_superuser
        token['is_management'] = user.is_management
        token['is_teacher'] = user.is_teacher
        token['is_driver'] = user.is_driver
        token['is_student'] = user.is_student
        token['is_parent'] = user.is_parent
        return token

    def validate(self, attrs):
        username_input = attrs.get('username')
        
        if username_input and '@' in username_input:
            try:
                user = User.objects.get(email=username_input)
                attrs['username'] = user.username
            except User.DoesNotExist:
                # Let it fail with invalid credentials later, 
                # or raise a specific error here if preferred.
                pass
        
        # Check for blocked user
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            try:
                # Resolve user just like above (or use email if that was swapped)
                # The logic above might have swapped attrs['username'] to the user.username from email
                # So we can safely look up by username=attrs['username']
                user = User.objects.get(username=attrs['username'])
                if user.check_password(password):
                    if not user.is_active:
                         raise serializers.ValidationError({"detail": "Blocked or Contact Admin"})
            except User.DoesNotExist:
                pass

        data = super().validate(attrs)
        # return full user data along with token
        data['user'] = UserSerializer(self.user).data
        return data

from .models import Bus

class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ['id', 'bus_number', 'destination', 'number_plate', 'photo', 'management', 'morning_trip_end_time', 'evening_trip_start_time']
        read_only_fields = ['management']
