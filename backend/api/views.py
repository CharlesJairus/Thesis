from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer, StudentSerializer, StudentLogsSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Student, StudentQR, StudentAttendance , StudentLogs, Course
from django.shortcuts import get_object_or_404
import base64
import cv2
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.conf import settings
from rest_framework import status
from django.utils import timezone

import io

from .utils import generate_and_save_qr_to_model, qr_scanner , uniform_scanner

from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime

# Create your views here.


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['username'] = user.username
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)

        try:
            student = self.user.studentAccount
            data['role'] = 'Student'
            data['student'] = {
                'id': student.id,
                'fullName': student.fullName,
                'email': student.email,
                'course': student.course,
                'year_level': student.year_level,
            }
        except Student.DoesNotExist:
            data['role'] = 'Admin'
            data['admin'] = {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
            }

        return data
    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    
@api_view(['POST'])
def registerUser(request):
     if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({'message': 'User registered successfully'})
        return Response(serializer.errors, status=400)

class StudentView(ListCreateAPIView):
    serializer_class = StudentSerializer

    def get_queryset(self):
        return Student.objects.all().order_by('-created', '-update')

    def create(self, request, *args, **kwargs):
        print("Incoming Data:", request.data)

        course = request.data.get("course")
        print("Course ID:", course)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
        course_obj = get_object_or_404(Course, id=course)
        student = serializer.save(course=course_obj)

        
        instance = StudentQR.objects.create(student=student)
        generate_and_save_qr_to_model(student.studentCode, instance, student)
        instance.save()

        return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)
        
class StudentDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    
    def get_object(self):
        student_id = self.kwargs.get("pk")
        return get_object_or_404(Student, id=student_id)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()
        

@api_view(['POST'])
def qr_scanner_view(request):
    image_file = request.FILES.get("image")
    if not image_file:
        return Response({'error': 'No file provided'}, status=400)

    decoded_data = qr_scanner(image_file)
    if not decoded_data:
        return Response({'error': 'Invalid or unreadable QR code'}, status=400)

    student = Student.objects.filter(studentCode=decoded_data).first()
    if student:
        serializer = StudentSerializer(student)
        return Response(serializer.data, status=200)
    else:
        return Response({'error': 'Student not found'}, status=404)
    
@api_view(['POST'])
def uniform_scanner_view(request,pk):
    
    print(request.data)
    
    student = get_object_or_404(Student, id=pk)
    if not student:
        return Response({'error': 'Student not found'}, status=404)
    
    image_file = request.FILES.get("image")
    
    if not image_file:
        return Response({'error': 'No file provided'}, status=400)
    
   
    image_bytes = image_file.read()
    

    frame, detectedObjects = uniform_scanner(image_file,student)
    if frame is None:
        return Response({'error': 'Failed to process image'}, status=500)

    
    
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

    return Response({'image': jpg_as_text, "detectedObjects": detectedObjects}, status=200)


@api_view(['GET'])
def student_logs(request):
    studentLogs = StudentLogs.objects.all()
    serializer = StudentLogsSerializer(studentLogs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def compliance_data(request):
    try:
        # Daily aggregation
        daily_qs = (
            StudentLogs.objects
            .annotate(day=TruncDay('timestamp'))
            .values('day')
            .annotate(
                compliant=Count('id', filter=Q(log_type='CU')),
                nonCompliant=Count('id', filter=Q(log_type='IU'))
            )
            .order_by('day')
        )

        daily = []
        for d in daily_qs:
            if d['day']:  # Check if day is not None
                # Handle both timezone-aware and naive datetimes
                day_date = d['day']
                if hasattr(day_date, 'strftime'):
                    date_str = day_date.strftime("%Y-%m-%d")
                else:
                    # If it's already a string, parse it first
                    parsed_date = parse_datetime(str(day_date))
                    if parsed_date:
                        date_str = parsed_date.strftime("%Y-%m-%d")
                    else:
                        continue  # Skip invalid dates
                
                daily.append({
                    "date": date_str,
                    "compliant": d['compliant'],
                    "nonCompliant": d['nonCompliant']
                })

        # Weekly aggregation
        weekly_qs = (
            StudentLogs.objects
            .annotate(week=TruncWeek('timestamp'))
            .values('week')
            .annotate(
                compliant=Count('id', filter=Q(log_type='CU')),
                nonCompliant=Count('id', filter=Q(log_type='IU'))
            )
            .order_by('week')
        )

        weekly = []
        for d in weekly_qs:
            if d['week']:  # Check if week is not None
                week_date = d['week']
                if hasattr(week_date, 'strftime'):
                    week_str = f"Week of {week_date.strftime('%Y-%m-%d')}"
                else:
                    parsed_date = parse_datetime(str(week_date))
                    if parsed_date:
                        week_str = f"Week of {parsed_date.strftime('%Y-%m-%d')}"
                    else:
                        continue
                
                weekly.append({
                    "week": week_str,
                    "compliant": d['compliant'],
                    "nonCompliant": d['nonCompliant']
                })

        # Monthly aggregation
        monthly_qs = (
            StudentLogs.objects
            .annotate(month=TruncMonth('timestamp'))
            .values('month')
            .annotate(
                compliant=Count('id', filter=Q(log_type='CU')),
                nonCompliant=Count('id', filter=Q(log_type='IU'))
            )
            .order_by('month')
        )

        monthly = []
        for d in monthly_qs:
            if d['month']:  # Check if month is not None
                month_date = d['month']
                if hasattr(month_date, 'strftime'):
                    month_str = month_date.strftime('%B %Y')  # Added year for clarity
                else:
                    parsed_date = parse_datetime(str(month_date))
                    if parsed_date:
                        month_str = parsed_date.strftime('%B %Y')
                    else:
                        continue
                
                monthly.append({
                    "month": month_str,
                    "compliant": d['compliant'],
                    "nonCompliant": d['nonCompliant']
                })

        # Course + Year aggregation
        logs = (
            StudentLogs.objects
            .select_related('student__course')  # Optimize database queries
            .values('student__course__name', 'student__year_level')
            .annotate(
                compliant=Count('id', filter=Q(log_type='CU')),
                nonCompliant=Count('id', filter=Q(log_type='IU'))
            )
            .order_by('student__course__name', 'student__year_level')
        )

        course_map = {}
        for entry in logs:
            course = entry['student__course__name']
            year = entry['student__year_level']

            # Skip entries with missing data
            if not course or not year:
                continue

            if course not in course_map:
                course_map[course] = []

            # Handle year suffixes more robustly
            if year in [1, 21, 31, 41, 51, 61, 71, 81, 91]:
                suffix = "st"
            elif year in [2, 22, 32, 42, 52, 62, 72, 82, 92]:
                suffix = "nd"
            elif year in [3, 23, 33, 43, 53, 63, 73, 83, 93]:
                suffix = "rd"
            else:
                suffix = "th"

            course_map[course].append({
                "year": f"{year}{suffix} Year",
                "compliant": entry['compliant'],
                "nonCompliant": entry['nonCompliant']
            })

        course_year_data = [
            {
                "course": course,
                "years": year_data
            }
            for course, year_data in course_map.items()
        ]

        return JsonResponse({
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "courseYearData": course_year_data
        })

    except Exception as e:
        # Log the error in production
        
        return JsonResponse({
            "error": "An error occurred while fetching compliance data",
            "daily": [],
            "weekly": [],
            "monthly": [],
            "courseYearData": []
        }, status=500)
        
@api_view(['POST'])
def wash_day(request, pk):
    student = get_object_or_404(Student, id=pk)

    StudentLogs.objects.create(
        student=student, 
        log_type='CU',
        timestamp=timezone.now()
    )

    email = EmailMessage(
        subject='[Uniform Scanner] Detection Summary',
        body=(
            f"Dear {student.fullName},\n\n"
            f"This is to inform you that your recent scan has been processed.\n\n"
            f"Details:\n Today is Wash Day \n\n"
            f"Since Today is Wash Day the QR detection is for Attendance\n\n"
            f"If this detection appears incorrect, please contact your supervisor.\n\n"
            f"Regards,\nUniform Monitoring System"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['faceless7078@gmail.com', student.email],
    )
    email.send()

   
    return Response({
        'message': 'Log created successfully for Wash Day.',
        'student': student.fullName,
        'email_sent': True
    })
    
   