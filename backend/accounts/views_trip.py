from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Trip, Bus
from django.utils import timezone

class StartTripView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        bus = request.user.bus
        if not bus:
            return Response({'error': 'No bus assigned'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Determine Trip Type based on the bus schedule
        now = timezone.localtime()
        current_time = now.time()
        
        if current_time < bus.evening_trip_start_time:
            trip_type = 'morning'
        else:
            trip_type = 'evening'


        # End any existing active trips for this bus (Safety cleanup)
        Trip.objects.filter(bus=bus, is_active=True).update(is_active=False, end_time=timezone.now())
        
        trip = Trip.objects.create(bus=bus, driver=request.user, trip_type=trip_type)
        return Response({
            'message': f'{trip_type.capitalize()} Trip started', 
            'trip_id': trip.id,
            'trip_type': trip_type
        }, status=status.HTTP_201_CREATED)

class EndTripView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        bus = request.user.bus
        if not bus:
             return Response({'error': 'No bus assigned'}, status=status.HTTP_400_BAD_REQUEST)

        Trip.objects.filter(bus=bus, is_active=True).update(is_active=False, end_time=timezone.now())
        
        # Clear location data
        bus.latitude = None
        bus.longitude = None
        bus.last_update = None
        bus.save()
        
        return Response({'message': 'Trip ended'}, status=status.HTTP_200_OK)

class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if not latitude or not longitude:
            return Response({'error': 'Missing coordinates'}, status=status.HTTP_400_BAD_REQUEST)
            
        bus = request.user.bus
        if not bus:
             return Response({'error': 'No bus assigned'}, status=status.HTTP_400_BAD_REQUEST)
             
        # Update Bus Location
        # Check if there is an active trip for this bus
        try:
             trip = Trip.objects.get(bus=bus, is_active=True)
        except Trip.DoesNotExist:
             return Response({'error': 'No active trip for this bus.'}, status=status.HTTP_400_BAD_REQUEST)

        bus.latitude = latitude
        bus.longitude = longitude
        bus.last_update = timezone.now()
        bus.save()
        
        return Response({'message': 'Location updated'}, status=status.HTTP_200_OK)

class BusLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bus_id):
        try:
            bus = Bus.objects.get(id=bus_id)
            user = request.user
            
            # Permission Check
            has_permission = False
            
            if user.is_superuser:
                has_permission = True
            elif user.is_management:
                if bus.management == user:
                    has_permission = True
            elif user.is_driver:
                if user.bus == bus:
                    has_permission = True
            elif user.is_student or user.is_teacher:
                if user.bus == bus:
                    has_permission = True
            elif user.is_parent:
                # Check if any child is assigned to this bus
                if user.children.filter(bus=bus).exists():
                    has_permission = True
            
            if not has_permission:
                return Response({'error': 'You do not have permission to track this bus.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if there is an active trip
            active_trip = Trip.objects.filter(bus=bus, is_active=True).exists()
            
            data = {
                'bus_id': bus.id,
                'bus_number': bus.bus_number,
                'is_active_trip': active_trip,
                'latitude': bus.latitude,
                'longitude': bus.longitude,
                'last_update': bus.last_update
            }
            return Response(data, status=status.HTTP_200_OK)
        except Bus.DoesNotExist:
            return Response({'error': 'Bus not found'}, status=status.HTTP_404_NOT_FOUND)
