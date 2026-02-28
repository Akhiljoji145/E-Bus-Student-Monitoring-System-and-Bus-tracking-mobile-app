from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from .models import Bus, BoardingLog, Notification

User = get_user_model()

class DriverDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied. Not a driver.'}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        bus = user.bus

        if not bus:
            return Response({
                'bus': None,
                'trip': {'type': 'No Trip Assigned', 'status': 'Inactive'},
                'route': {'name': 'N/A', 'start': 'N/A', 'end': 'N/A'},
                'boarding': {'boarded': 0, 'expected': 0},
                'students': [],
                'alerts': []
            })

        # Fetch Active Trip
        from .models import Trip
        current_trip = Trip.objects.filter(bus=bus, is_active=True).first()

        current_time = timezone.localtime().time()
        if current_time >= bus.evening_trip_start_time:
            predicted_type_display = 'Evening'
            route_data = {
                'name': 'Evening Drop-off',
                'start': 'College Campus',
                'end': bus.destination or 'Drop-offs'
            }
        else:
            predicted_type_display = 'Morning'
            route_data = {
                'name': 'Morning Pickup',
                'start': 'Pickups',
                'end': 'College Campus'
            }

        trip_data = {
            'type': f'{predicted_type_display} Trip (Scheduled)',
            'status': 'Scheduled'
        }

        if current_trip:
            trip_data = {
                'type': f"{current_trip.get_trip_type_display()} Trip",
                'status': 'Ongoing'
            }
            
            if current_trip.trip_type == 'morning':
                route_data = {
                    'name': 'Morning Pickup',
                    'start': 'Pickups',
                    'end': 'College Campus'
                }
            else:
                route_data = {
                    'name': 'Evening Drop-off',
                    'start': 'College Campus',
                    'end': bus.destination or 'Drop-offs'
                }

        # Fetch students assigned to this bus
        students = User.objects.filter(bus=bus, is_student=True).values('id', 'username', 'email', 'first_name', 'last_name')
        expected_count = students.count()
        
        # Real Boarding Data for TODAY
        today = timezone.localtime().date()
        
        # Filter logs by current trip if active, else just today
        if current_trip:
            boarding_logs = BoardingLog.objects.filter(bus=bus, trip=current_trip).select_related('student')
        else:
            # If no active trip, show nothing or maybe today's logs? 
            # Better to show nothing for "Current Trip Status" context, but maybe historical?
            # Let's show today's logs generally if no trip, but specific trip logs if active.
            boarding_logs = BoardingLog.objects.filter(bus=bus, date=today).select_related('student')

        boarded_student_ids = set(log.student.id for log in boarding_logs)
        boarded_map = {log.student.id: log.scan_time.strftime('%I:%M %p') for log in boarding_logs}
        
        boarded_count = len(boarded_student_ids)

        student_list = []
        for s in students:
            is_boarded = s['id'] in boarded_student_ids
            scan_time = boarded_map.get(s['id'], '-')
            
            # Use First Name if available, else Username
            display_name = s['first_name'] if s['first_name'] else s['username']
            if s['last_name']:
                display_name += f" {s['last_name']}"

            student_list.append({
                'id': s['id'],
                'name': display_name,
                'status': 'Boarded' if is_boarded else 'Pending',
                'time': scan_time
            })

        data = {
            'bus': {
                'id': bus.id,
                'number': bus.bus_number,
                'status': 'Active',
                'plate': bus.number_plate
            },
            'qr_token': TimestampSigner().sign(bus.id), # Generate signed token associated with bus ID
            'trip': trip_data,
            'route': route_data,
            'boarding': {
                'boarded': boarded_count,
                'expected': expected_count
            },
            'location': {
                'gps': True,
                'lastUpdated': 'Just now'
            },
            'students': student_list,
            'alerts': [
                {'id': 1, 'title': 'System Update', 'message': 'Syncing new route data.', 'time': '08:00 AM'}
            ]
        }

        return Response(data)

class DriverBroadcastView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied. Not a driver.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Notification is now imported at module level
        # Fetch last 10 notifications sent by this user
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        history = []
        for n in notifications:
            history.append({
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'created_at': n.created_at.strftime("%b %d, %I:%M %p") 
            })
            
        return Response(history)

    def post(self, request):
        if not request.user.is_driver:
            return Response({'error': 'Permission denied. Not a driver.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        alert_type = data.get('type')
        message = data.get('message')
        phone = data.get('phone')

        if not message:
             return Response({'error': 'Message required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Access Driver's Bus
        bus = request.user.bus
        if not bus:
            return Response({'error': 'No bus assigned to your account.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Get Students on this Bus
        students = User.objects.filter(bus=bus, is_student=True)
        
        # 3. Collect Emails (Student + Parent)
        recipient_list = []
        for student in students:
            if student.email:
                recipient_list.append(student.email)
            if student.parent and student.parent.email:
                recipient_list.append(student.parent.email)
        
        recipient_list = list(set(recipient_list)) # Remove duplicates

        if not recipient_list:
             return Response({'message': 'No students/parents found with email addresses.'}, status=status.HTTP_200_OK)

        # 4. Send Email
        from django.core.mail import send_mail
        from .utils import send_push_notification
        
        # Collect Push Tokens
        push_tokens = []
        for student in students:
            if student.push_token:
                push_tokens.append(student.push_token)
            if student.parent and student.parent.push_token:
                push_tokens.append(student.parent.push_token)
        
        # Send Push Notification
        if push_tokens:
            send_push_notification(
                tokens=push_tokens,
                title=f"Transport Alert: {alert_type}",
                message=message,
                data={'type': alert_type, 'bus_id': bus.id}
            )

        try:
            send_mail(
                subject=f"Transport Alert: {alert_type}",
                message=f"""
Dear Student/Parent,

This is an alert regarding Bus {bus.bus_number}.

Update: {alert_type}
Message: {message}

Driver Contact: {phone}

Regards,
School Transport Team
                """,
                from_email=None, # Configure this in settings.py
                recipient_list=recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email error: {e}")
            # Continue to save notification even if email fails
        
        Notification.objects.create(
            user=request.user, 
            title=f"Broadcast to {len(recipient_list)} recipients", 
            message=f"{message}", 
            type='success'
        )

        return Response({'message': f'Broadcast sent to {len(recipient_list)} recipients successfully'}, status=status.HTTP_200_OK)

class StudentBoardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_student:
             return Response({'error': 'Permission denied. Not a student.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        qr_token = data.get('qr_token')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not qr_token:
             return Response({'error': 'QR Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify QR Token
        try:
            # Valid for 35 seconds (slightly more than the refresh rate of 30s to account for network latency)
            bus_id = TimestampSigner().unsign(qr_token, max_age=35) 
        except SignatureExpired:
            return Response({'error': 'QR Code has expired. Please ask driver to refresh.'}, status=status.HTTP_400_BAD_REQUEST)
        except BadSignature:
            return Response({'error': 'Invalid QR Code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify Bus
        try:
            bus = Bus.objects.get(id=bus_id)
        except Bus.DoesNotExist:
             return Response({'error': 'Invalid Bus ID.'}, status=status.HTTP_404_NOT_FOUND)
             
        # Check for Active Trip
        from .models import Trip
        try:
            current_trip = Trip.objects.get(bus=bus, is_active=True)
        except Trip.DoesNotExist:
             return Response({'error': 'No active trip for this bus. Driver must start trip first.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if student is assigned to this bus (Optional strict check)
        # if request.user.bus != bus:
        #     return Response({'error': 'You are not assigned to this bus.'}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent duplicate boarding for the same TRIP
        from .models import BoardingLog

        if BoardingLog.objects.filter(student=request.user, trip=current_trip).exists():
            return Response({'message': 'Already boarded for this trip.', 'status': 'already_boarded'}, status=status.HTTP_200_OK)

        # Create Log
        BoardingLog.objects.create(
            student=request.user,
            bus=bus,
            trip=current_trip,
            latitude=latitude,
            longitude=longitude
        )

        return Response({
            'message': 'Boarding successful!', 
            'bus': bus.bus_number,
            'time': timezone.localtime().strftime('%I:%M %p')
        }, status=status.HTTP_201_CREATED)
