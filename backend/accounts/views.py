from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MyTokenObtainPairSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetForm(data=request.data)
        if serializer.is_valid():
            serializer.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
                from_email=None
            )
            return Response({"success": True, "message": "Password reset link sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmAPIView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')

        if not uidb64 or not token or not password:
             return Response({'error': 'Missing parameters'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str
            from django.contrib.auth.tokens import default_token_generator
            
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                return Response({'success': True, 'message': 'Password has been reset successfully.'})
            else:
                return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

from .models import PasswordResetOTP
import random
from django.core.mail import send_mail

class SendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email__iexact=email)
            otp = str(random.randint(100000, 999999))
            
            # Save OTP (update existing or create new)
            PasswordResetOTP.objects.update_or_create(
                user=user,
                defaults={'otp': otp, 'created_at': timezone.now()}
            )
            
            # Send Email
            try:
                send_mail(
                    'Password Reset OTP',
                    f'Your OTP for password reset is: {otp}',
                    None,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send email to {email}: {e}")
                return Response({'error': f'Failed to send email. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({'success': True, 'message': 'OTP sent to email.'})
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = User.objects.get(email__iexact=email)
            otp_record = PasswordResetOTP.objects.get(user=user)
            
            if otp_record.otp == otp and otp_record.is_valid():
                return Response({'success': True, 'message': 'OTP verified.'})
            else:
                return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
             return Response({'error': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        password = request.data.get('password')
        
        try:
            user = User.objects.get(email__iexact=email)
            otp_record = PasswordResetOTP.objects.get(user=user)
            
            if otp_record.otp == otp and otp_record.is_valid():
                user.set_password(password)
                user.save()
                otp_record.delete() # Consume OTP
                return Response({'success': True, 'message': 'Password reset successfully.'})
            else:
                return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
