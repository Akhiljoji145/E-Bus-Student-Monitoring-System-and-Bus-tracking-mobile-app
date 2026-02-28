from django.urls import path
from .views import MyTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmAPIView, SendOTPView, VerifyOTPView, ResetPasswordOTPView
from django.contrib.auth import views as auth_views
from .views_management import (
    RegisterManagementView, 
    DashboardStatsView, 
    UserListView, 
    DeleteUserView,
    DeleteUserView,
    RegisterMemberView,
    RegisterMemberView,
    BusListView,
    GradeListView,
    UpdateMemberView,
    ToggleBlockUserView,
    RegisterBusView,
    BusDetailView,
    UserProfileView,
    ManagementComplaintListView,
    ManagementComplaintDetailView
)
from .views_driver import DriverDashboardStatsView, DriverBroadcastView, StudentBoardingView
from .views_student import StudentDashboardView, StudentComplaintView
from .views_parent import ParentDashboardView, ParentComplaintView
from .views_trip import StartTripView, EndTripView, UpdateLocationView, BusLocationView
from .views_teacher import TeacherDashboardStatsView, TeacherStudentListView, TeacherAlertsView, UpdateStudentStatusView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/management/', RegisterManagementView.as_view(), name='register_management'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/me/', UserProfileView.as_view(), name='user_profile'),
    path('users/<int:pk>/delete/', DeleteUserView.as_view(), name='delete_user'),
    path('users/<int:pk>/toggle-block/', ToggleBlockUserView.as_view(), name='toggle_block_user'),
    path('register/member/', RegisterMemberView.as_view(), name='register_member'),
    path('dashboard/buses/', BusListView.as_view(), name='bus_list'),
    path('dashboard/buses/<int:pk>/', BusDetailView.as_view(), name='bus_detail'),
    path('dashboard/add-bus/', RegisterBusView.as_view(), name='add_bus'),
    path('dashboard/complaints/', ManagementComplaintListView.as_view(), name='management_complaint_list'),
    path('dashboard/complaints/<int:pk>/', ManagementComplaintDetailView.as_view(), name='management_complaint_detail'),
    path('dashboard/grades/', GradeListView.as_view(), name='grade_list'),
    path('users/<int:pk>/update/', UpdateMemberView.as_view(), name='update_user'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='password_reset_confirm_api'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password-reset/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('password-reset/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('password-reset/reset-with-otp/', ResetPasswordOTPView.as_view(), name='reset_with_otp'),
    path('dashboard/driver/stats/', DriverDashboardStatsView.as_view(), name='driver_dashboard_stats'),
    path('dashboard/driver/broadcast/', DriverBroadcastView.as_view(), name='driver_broadcast'),
    path('dashboard/student/board/', StudentBoardingView.as_view(), name='student_board'),
    path('trip/start/', StartTripView.as_view(), name='start_trip'),
    path('trip/end/', EndTripView.as_view(), name='end_trip'),
    path('trip/update-location/', UpdateLocationView.as_view(), name='update_location'),
    path('trip/bus-location/<int:bus_id>/', BusLocationView.as_view(), name='bus_location'),
    
    # Student Endpoints
    path('student/dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('student/complaints/', StudentComplaintView.as_view(), name='student_complaints'),

    # Parent Endpoints
    path('parent/dashboard/', ParentDashboardView.as_view(), name='parent_dashboard'),
    path('parent/complaints/', ParentComplaintView.as_view(), name='parent_complaints'),

    # Teacher Endpoints
    path('teacher/dashboard/stats/', TeacherDashboardStatsView.as_view(), name='teacher_dashboard_stats'),
    path('teacher/students/', TeacherStudentListView.as_view(), name='teacher_student_list'),
    path('teacher/alerts/', TeacherAlertsView.as_view(), name='teacher_alerts'),
    path('teacher/student/update-status/', UpdateStudentStatusView.as_view(), name='teacher_update_student_status'),
]
