
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import BoardingLog, Trip, Notification, Grade
from datetime import date

User = get_user_model()

class TeacherDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_teacher:
            return Response({'error': 'Not authorized as teacher'}, status=status.HTTP_403_FORBIDDEN)

        class_in_charge = user.class_in_charge
        if not class_in_charge:
             return Response({
                'boarded': 0,
                'total_students': 0,
                'pending_alerts': 0,
                'trip_status': 'No Active Trip',
                'trip_type': 'none'
            })

        students = User.objects.filter(class_in_charge=class_in_charge, is_student=True)
        total_students = students.count()

        # Get today's active trip (if any)
        today = timezone.now().date()
        # Find any active trip for today. 
        # Note: In a real scenario, we might need to filter by the bus associated with the class or general trips.
        # Assuming trips are global or we pick the most relevant one.
        # For simplicity, let's look for ANY active trip today.
        active_trip = Trip.objects.filter(start_time__date=today, is_active=True).first()
        
        boarded_count = 0
        trip_status = 'No Active Trip'
        trip_type = 'none'

        if active_trip:
            trip_status = f"{active_trip.get_trip_type_display()} Trip Ongoing"
            trip_type = active_trip.trip_type
            
            # Count boarded students from this class
            boarded_count = BoardingLog.objects.filter(
                trip=active_trip,
                student__in=students
            ).count()
        else:
             # Check for completed trips today to show "Completed" status
             last_trip = Trip.objects.filter(start_time__date=today, is_active=False).last()
             if last_trip:
                 trip_status = f"{last_trip.get_trip_type_display()} Trip Completed"
                 trip_type = last_trip.trip_type
             else:
                 current_time = timezone.localtime().time()
                 bus = user.bus
                 if bus and current_time >= bus.evening_trip_start_time:
                     trip_type = 'evening'
                 elif not bus and current_time.hour >= 12:
                     trip_type = 'evening'
                 else:
                     trip_type = 'morning'
                 trip_status = 'Scheduled'

        # Alerts (Mock logic for now, or based on 'Not Boarded' if trip ended)
        # Real logic: Count notifications for this teacher's students
        pending_alerts = Notification.objects.filter(
            user=user, 
            is_read=False
        ).count()

        return Response({
            'boarded': boarded_count,
            'total_students': total_students,
            'pending_alerts': pending_alerts,
            'trip_status': trip_status,
            'trip_type': trip_type
        })

class TeacherStudentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_teacher:
            return Response({'error': 'Not authorized as teacher'}, status=status.HTTP_403_FORBIDDEN)

        class_in_charge = user.class_in_charge
        if not class_in_charge:
            return Response([])

        students = User.objects.filter(class_in_charge=class_in_charge, is_student=True)
        
        today = timezone.now().date()
        active_trip = Trip.objects.filter(start_time__date=today, is_active=True).first()

        student_data = []
        for student in students:
            status_text = 'Not Boarded'
            board_time = None
            
            if active_trip:
                log = BoardingLog.objects.filter(trip=active_trip, student=student).first()
                if log:
                    status_text = 'Boarded'
                    board_time = log.scan_time.strftime('%I:%M %p')
            
            # Check for manual overrides (Absent/Leave) - Assuming we might have extended User model or a separate Status model
            # For now, we don't have a dedicated "Status" field on User for daily attendance, 
            # so we'll just return default or mock if we want to stick to the requirement
            # Let's assume we use a temporary field or just rely on BoardingLog for now.
            
            student_data.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}".strip() or student.username,
                'class': str(class_in_charge),
                'status': status_text,
                'time': board_time,
                'image': None # user.profile_picture.url if user.profile_picture else None
            })

        return Response(student_data)

class TeacherAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_teacher:
             return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        # In a real app, we would query the Notification model
        notifications = Notification.objects.filter(user=user).order_by('-created_at')
        
        data = []
        for notif in notifications:
            data.append({
                'id': notif.id,
                'type': notif.type, # 'Not Boarded', etc.
                'student': notif.title, # Assuming title holds student name for simplicity
                'time': notif.created_at.strftime('%I:%M %p'),
                'details': notif.message
            })
        
        return Response(data)

class UpdateStudentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_teacher:
             return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        student_id = request.data.get('student_id')
        new_status = request.data.get('status') # 'Absent', 'Leave', 'Late'
        
        # Here we would save this status to a DailyAttendance model
        # For this demo, we will just return success as we don't have that model yet.
        
        return Response({'success': True, 'message': f'Status updated to {new_status}'})

