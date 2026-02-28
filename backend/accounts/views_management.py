from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils.crypto import get_random_string


from .models import Bus, Grade, Complaint

User = get_user_model()

class RegisterManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only admins or management can create new management users
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        username = data.get('username')
        email = data.get('email')
        phone = data.get('phone') 

        if not username or not email:
            return Response({'error': 'Username and Email are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate random password
        password = get_random_string(length=10)

        try:
            # Pass all extra fields to create_user or set them after
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=password,
                phone=phone,
                organization_name=data.get('organization_name')
            )
            user.is_management = True
            user.save()

            # Send Email
            try:
                subject = 'Your Management Account Credentials'
                message = f"""
                Hello {username},

                Your management account has been created for {data.get('organization_name', 'our organization')}.

                Here are your login credentials:
                Username: {username}
                Password: {password}

                Please login and change your password immediately.

                Regards,
                Admin Team
                """
                
                send_mail(
                    subject,
                    message,
                    None,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email to management user {email}: {e}")

            return Response({'message': 'Management user created and email sent successfully'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.is_superuser:
            total_users = User.objects.count()
            # Verified Institutions logic: is_management=True AND is_active=True
            verified_institutions = User.objects.filter(is_management=True, is_active=True).count()
            # Pending Institution Verifications logic: is_management=True AND is_active=False
            pending_institutions = User.objects.filter(is_management=True, is_active=False).count()
            
            management_users = verified_institutions + pending_institutions # total management users
            active_users = User.objects.filter(is_active=True).count()
            total_buses = Bus.objects.count() # Superuser sees all buses

            # Active users per management
            management_breakdown = []
            verified_admins = User.objects.filter(is_management=True, is_active=True)
            for admin in verified_admins:
                count = User.objects.filter(managed_by=admin, is_active=True).count()
                management_breakdown.append({
                    'id': admin.id,
                    'username': admin.username,
                    'email': admin.email,
                    'active_users': count
                })

        else:
            # Management view: only their managed members
            total_users = User.objects.filter(managed_by=request.user).count()
            verified_institutions = 0 
            pending_institutions = 0
            management_users = 0 
            active_users = User.objects.filter(managed_by=request.user, is_active=True).count()
            total_buses = Bus.objects.filter(management=request.user).count() # Only their buses
            management_breakdown = []
        
        # Mock Revenue Calculation
        revenue = total_users * 120 # Assuming $120 ARPU

        # Open Complaints
        if request.user.is_superuser:
            open_complaints = Complaint.objects.filter(status__in=['submitted', 'in_action']).count()
        else:
            # Get students managed by this user
            student_ids = User.objects.filter(managed_by=request.user).values_list('id', flat=True)
            open_complaints = Complaint.objects.filter(user__id__in=student_ids, status__in=['submitted', 'in_action']).count()
        
        return Response({
            'total_users': total_users,
            'management_users': management_users,
            'verified_institutions': verified_institutions,
            'pending_institutions': pending_institutions,
            'active_users': active_users,
            'total_buses': total_buses,
            'management_breakdown': management_breakdown,
            'revenue': revenue,
            'open_complaints': open_complaints
        })

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.is_superuser:
            users = User.objects.all().values('id', 'username', 'email', 'is_superuser', 'is_management', 'is_teacher', 'is_driver', 'is_parent', 'is_student', 'is_active', 'phone', 'organization_name')
        else:
            users = User.objects.filter(managed_by=request.user).values('id', 'username', 'email', 'is_superuser', 'is_management', 'is_teacher', 'is_driver', 'is_parent', 'is_student', 'is_active', 'phone', 'organization_name')
        return Response(list(users))

class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
            
            # Authorization Check
            if not request.user.is_superuser:
                if user.managed_by != request.user:
                     return Response({'error': 'You do not have permission to delete this user.'}, status=status.HTTP_403_FORBIDDEN)

            # Prevent deleting yourself
            if user.id == request.user.id:
                 return Response({'error': 'You cannot delete your own account.'}, status=status.HTTP_400_BAD_REQUEST)

            user.delete()
            return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class ToggleBlockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
            
            # Authorization Check
            if not request.user.is_superuser:
                 # Managers can only block their own users
                if user.managed_by != request.user:
                     return Response({'error': 'You do not have permission to modify this user.'}, status=status.HTTP_403_FORBIDDEN)

            # Prevent blocking yourself
            if user.id == request.user.id:
                 return Response({'error': 'You cannot block your own account.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Toggle is_active
            user.is_active = not user.is_active
            user.save()
            
            status_msg = "blocked" if not user.is_active else "unblocked"
            return Response({'message': f'User {status_msg} successfully', 'is_active': user.is_active}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class RegisterMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.is_management or request.user.is_superuser):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role')
        username = request.data.get('username')
        email = request.data.get('email')
        phone = request.data.get('phone')

        if not all([role, username, email]):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Generate Random Password
            password = get_random_string(length=10)

            # 2. Define User Flags
            user_data = {
                'username': username,
                'email': email,
                'password': password,
                'is_staff': False
            }

            if role == 'teacher':
                user_data['is_teacher'] = True
                # Handle class and bus assignments
                class_in_charge_id = request.data.get('class_in_charge')
                bus_id = request.data.get('bus')
                
                if class_in_charge_id:
                    try:
                        user_data['class_in_charge'] = Grade.objects.get(id=class_in_charge_id)
                    except Grade.DoesNotExist:
                        pass # Ignore invalid IDs
                
                if bus_id:
                    try:
                        user_data['bus'] = Bus.objects.get(id=bus_id)
                    except Bus.DoesNotExist:
                        pass
            elif role == 'driver':
                user_data['is_driver'] = True
                bus_id = request.data.get('bus')
                if bus_id:
                    try:
                        user_data['bus'] = Bus.objects.get(id=bus_id)
                    except Bus.DoesNotExist:
                        pass
            elif role == 'student':
                user_data['is_student'] = True
                # Handle bus and class assignment for students
                bus_id = request.data.get('bus')
                class_in_charge_id = request.data.get('class_in_charge')
                
                if bus_id:
                    try:
                        user_data['bus'] = Bus.objects.get(id=bus_id)
                    except Bus.DoesNotExist:
                        pass
                
                if class_in_charge_id:
                    try:
                        user_data['class_in_charge'] = Grade.objects.get(id=class_in_charge_id)
                    except Grade.DoesNotExist:
                        pass # Ignore invalid IDs
            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Create Member User
            user = User.objects.create_user(**user_data)
            
            # Associate with Management User if creator is management
            if request.user.is_management:
                user.managed_by = request.user
                user.save()
            
            # Send Email to Member
            try:
                send_mail(
                    subject='Account Created',
                    message=f'Your {role} account has been created.\nUsername: {username}\nPassword: {password}',
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email to member {email}: {e}")

            response_data = {
                "message": f"{role.capitalize()} account created successfully",
                "member_username": username,
                "member_password": password 
            }

            # 4. Handle Student Parent Creation
            if role == 'student':
                parent_data = request.data.get('parent_details')
                if not parent_data:
                    # Cleanup if parent missing
                    user.delete()
                    return Response({"error": "Parent details required for students"}, status=status.HTTP_400_BAD_REQUEST)
                
                parent_name = parent_data.get('name')
                parent_email = parent_data.get('email')
                
                # Generate Parent Password
                parent_password = get_random_string(length=10)
                
                # Create Parent User
                parent_user = User.objects.create_user(
                    username=parent_name, # Assuming unique, might need uniqueness check logic in real app
                    email=parent_email,
                    password=parent_password,
                    is_parent=True
                )

                # Link Parent to Student
                user.parent = parent_user
                user.save()
                
                # Associate Parent with Management User too
                if request.user.is_management:
                    parent_user.managed_by = request.user
                    parent_user.save()

                # Send Email to Parent
                try:
                    parent_msg = f"""
                    Hello {parent_name},

                    Your parent account has been created.
                    Username: {parent_name}
                    Password: {parent_password}

                    Your Child's ({username}) Login Details:
                    Username: {username}
                    Password: {password}

                    Please login to manage your child's activities.
                    """

                    send_mail(
                        subject='Parent & Student Account Created',
                        message=parent_msg,
                        from_email=None,
                        recipient_list=[parent_email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send email to parent {parent_email}: {e}")
                
                response_data["parent_username"] = parent_name
                response_data["parent_password"] = parent_password

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BusListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            buses = Bus.objects.all()
        elif request.user.is_management:
            buses = Bus.objects.filter(management=request.user)
        else:
             # Basic users/members might need to see buses linked to them or all buses?
             # For now, let's show all buses to members effectively, or restrict. 
             # Logic implies member registration needs to see buses to pick one.
             # Ideally members pick from their manager's buses if invited? 
             # For now, let's keeping it simple: if part of organization, see organization buses.
             # If user has 'managed_by', show those buses.
             if request.user.managed_by:
                buses = Bus.objects.filter(management=request.user.managed_by)
             else:
                buses = Bus.objects.all() # Fallback

        data = BusSerializer(buses, many=True).data 
        # Using Serializer to return full details for the list in dashboard
        return Response(data)

class GradeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grades = Grade.objects.all()
        data = [{'id': g.id, 'name': str(g)} for g in grades]
        return Response(data)

class UpdateMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if not (request.user.is_management or request.user.is_superuser):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(pk=pk)

            # Authorization Check
            if not request.user.is_superuser:
                # Allow user to update themselves
                if user.id != request.user.id and user.managed_by != request.user:
                     return Response({'error': 'You do not have permission to update this user.'}, status=status.HTTP_403_FORBIDDEN)

            data = request.data
            
            # Common Fields
            if 'username' in data: user.username = data['username']
            if 'email' in data: user.email = data['email']
            if 'phone' in data: user.phone = data['phone'] 
            if 'organization_name' in data: user.organization_name = data['organization_name']

            # Schedule Settings
            if 'morning_arrival_time' in data: user.morning_arrival_time = data['morning_arrival_time']
            if 'evening_departure_time' in data: user.evening_departure_time = data['evening_departure_time']

            # Teacher Fields
            if user.is_teacher:
                if 'class_in_charge' in data:
                    try:
                        user.class_in_charge = Grade.objects.get(id=data['class_in_charge']) if data['class_in_charge'] else None
                    except Grade.DoesNotExist:
                        pass
                if 'bus' in data:
                    try:
                        user.bus = Bus.objects.get(id=data['bus']) if data['bus'] else None
                    except Bus.DoesNotExist:
                        pass

            # Student/Parent Fields
            if user.is_student:
                if 'class_in_charge' in data:
                    try:
                        user.class_in_charge = Grade.objects.get(id=data['class_in_charge']) if data['class_in_charge'] else None
                    except Grade.DoesNotExist:
                        pass
                if 'bus' in data:
                    try:
                        user.bus = Bus.objects.get(id=data['bus']) if data['bus'] else None
                    except Bus.DoesNotExist:
                        pass

                if user.parent and 'parent_details' in data:
                    parent_data = data['parent_details']
                    parent = user.parent
                    if 'name' in parent_data: parent.username = parent_data['name'] # Using username as name
                    if 'email' in parent_data: parent.email = parent_data['email']
                    parent.save()

            user.save()
            return Response({'message': 'Member updated successfully'}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from .serializers import BusSerializer
from rest_framework.parsers import MultiPartParser, FormParser

class RegisterBusView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        if not (request.user.is_management or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = BusSerializer(data=request.data)
        if serializer.is_valid():
            # management field is read_only, so we assign it manually
            # if user is superuser, maybe they can assign to anyone? For now let's assume current user.
            # Or if superuser, maybe 'management' ID is passed?
            
            # For simplicity, assign to current user if they are management
            if request.user.is_management:
                serializer.save(management=request.user)
            else:
                serializer.save() # If superuser and logic not defined, create without management or rely on default? 
                                  # Model has null=True for management, so it's safe.
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BusDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self, pk, user):
        try:
            bus = Bus.objects.get(pk=pk)
            # Check permissions
            if user.is_superuser:
                return bus
            if bus.management == user:
                return bus
            return None
        except Bus.DoesNotExist:
            return None

    def put(self, request, pk):
        bus = self.get_object(pk, request.user)
        if not bus:
            return Response({'error': 'Bus not found or permission denied'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BusSerializer(bus, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        bus = self.get_object(pk, request.user)
        if not bus:
            return Response({'error': 'Bus not found or permission denied'}, status=status.HTTP_404_NOT_FOUND)
        
        bus.delete()
        return Response({'message': 'Bus deleted successfully'}, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import UserSerializer
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        from .serializers import UserSerializer
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ManagementComplaintListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Filter complaints:
        if request.user.is_superuser:
            complaints = Complaint.objects.all().order_by('-created_at')
        else:
            # Get students managed by this user
            student_ids = User.objects.filter(managed_by=request.user).values_list('id', flat=True)
            complaints = Complaint.objects.filter(user__id__in=student_ids).order_by('-created_at')

        data = []
        for c in complaints:
            data.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'status': c.status,
                'response': c.administrative_response,
                'date': c.created_at.strftime('%Y-%m-%d'),
                'student_name': c.user.username,
                'student_id': c.user.id,
                'student_email': c.user.email
            })
        
        return Response(data)

class ManagementComplaintDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not (request.user.is_superuser or request.user.is_management):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        try:
            complaint = Complaint.objects.get(pk=pk)
            
            # Authorization check
            if not request.user.is_superuser:
                 if complaint.user.managed_by != request.user:
                     return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

            data = request.data
            if 'status' in data:
                complaint.status = data['status']
            if 'response' in data:
                complaint.administrative_response = data['response']
            
            complaint.save()
            return Response({'message': 'Complaint updated successfully'})

        except Complaint.DoesNotExist:
            return Response({'error': 'Complaint not found'}, status=status.HTTP_404_NOT_FOUND)
