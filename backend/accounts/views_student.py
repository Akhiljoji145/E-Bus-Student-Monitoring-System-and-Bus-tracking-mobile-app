from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from .models import Bus, Trip, BoardingLog, Complaint, Notification

class StudentDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_student:
             return Response({'error': 'Not a student'}, status=status.HTTP_403_FORBIDDEN)

        # 1. Bus Info
        bus = user.bus
        bus_data = None
        if bus:
            bus_data = {
                'id': bus.id,
                'number': bus.bus_number,
                'plate': bus.number_plate,
                'driver_name': bus.trips.filter(is_active=True).first().driver.get_full_name() if bus.trips.filter(is_active=True).exists() else "N/A"
            }

        # 2. Today's Trip Status
        today = timezone.localtime().date()
        current_time = timezone.localtime().time()
        
        # Determine likely trip type based on time
        trip_type = 'morning'
        if bus and current_time >= bus.evening_trip_start_time:
             trip_type = 'evening'

        # Check for active trip
        active_trip = None
        if bus:
             active_trip = Trip.objects.filter(bus=bus, is_active=True).first()

        trip_status = {
            'type': trip_type.capitalize(),
            'status': 'Scheduled'
        }
        
        if active_trip:
            trip_status = {
                'type': active_trip.get_trip_type_display(),
                'status': 'Ongoing'
            }

        # 3. Boarding Status
        is_boarded = False
        if bus:
            # Check if boarded for *active* trip OR just today if no active trip
            if active_trip:
                is_boarded = BoardingLog.objects.filter(student=user, trip=active_trip).exists()
            else:
                 is_boarded = BoardingLog.objects.filter(student=user, date=today).exists()

        # 4. Notifications (Top 3)
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:3]
        notif_list = [{'id': n.id, 'title': n.title, 'message': n.message, 'time': n.created_at.strftime("%I:%M %p")} for n in notifications]

        return Response({
            'bus': bus_data,
            'trip': trip_status,
            'boarding': {'status': 'Boarded' if is_boarded else 'Not Boarded'},
            'notifications': notif_list
        })

class StudentComplaintView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            'id': c.id,
            'title': c.title,
            'description': c.description,
            'status': c.status,
            'response': c.administrative_response,
            'date': c.created_at.strftime("%d %b %Y")
        } for c in complaints]
        return Response(data)

    def post(self, request):
        title = request.data.get('title')
        description = request.data.get('description')
        
        if not title or not description:
            return Response({'error': 'Title and description required'}, status=status.HTTP_400_BAD_REQUEST)

        Complaint.objects.create(
            user=request.user,
            title=title,
            description=description
        )
        return Response({'message': 'Complaint submitted successfully'}, status=status.HTTP_201_CREATED)
