from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views


urlpatterns = [
    path('token', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh',TokenRefreshView.as_view(), name='token_refresh'),
    path('register/',views.registerUser),
    path('students/', views.StudentView.as_view()),
    path('student/<str:pk>/', views.StudentDetailView.as_view()),
    path('scan/qr', views.qr_scanner_view),
    path('scan/unif/<str:pk>/', views.uniform_scanner_view),
    path('logs/', views.student_logs),
    path('analytics/', views.compliance_data),
    path('washday/<str:pk>/', views.wash_day),
    
  
]


