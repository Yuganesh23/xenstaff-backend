from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.employees.models import Employee
from apps.attendance.models import (
    AttendanceEvent, DailyAttendanceSummary, AttendanceCorrection, CorrectionStatus, AttendanceStatus
)
from apps.attendance.serializers import (
    AttendanceEventSerializer, DailyAttendanceSummarySerializer,
    ClockInOutActionSerializer, AttendanceCorrectionSerializer
)
from apps.attendance.services import (
    record_clock_in, record_clock_out, approve_attendance_correction
)

class ClockInView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def post(self, request):
        serializer = ClockInOutActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Determine target employee: if employee_id provided and user is HR/Owner, allow; else use caller's profile
        employee_id = data.get('employee_id')
        if employee_id and request.organization_membership.role in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            employee = Employee.objects.filter(organization=request.organization, id=employee_id).first()
        else:
            employee = Employee.objects.filter(organization=request.organization, user=request.user).first()

        if not employee:
            return Response({'error': {'message': 'No employee profile linked to this user.'}}, status=status.HTTP_400_BAD_REQUEST)

        event, created = record_clock_in(
            organization=request.organization,
            employee=employee,
            idempotency_key=data['idempotency_key'],
            client_timestamp=data.get('client_timestamp'),
            source=data.get('source', 'WEB')
        )

        return Response({
            'success': True,
            'is_new': created,
            'event': AttendanceEventSerializer(event).data,
            'message': 'Clock-in recorded successfully.' if created else 'Duplicate clock-in request recognized.'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class ClockOutView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def post(self, request):
        serializer = ClockInOutActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee_id = data.get('employee_id')
        if employee_id and request.organization_membership.role in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            employee = Employee.objects.filter(organization=request.organization, id=employee_id).first()
        else:
            employee = Employee.objects.filter(organization=request.organization, user=request.user).first()

        if not employee:
            return Response({'error': {'message': 'No employee profile linked to this user.'}}, status=status.HTTP_400_BAD_REQUEST)

        event, created = record_clock_out(
            organization=request.organization,
            employee=employee,
            idempotency_key=data['idempotency_key'],
            client_timestamp=data.get('client_timestamp'),
            source=data.get('source', 'WEB')
        )

        return Response({
            'success': True,
            'is_new': created,
            'event': AttendanceEventSerializer(event).data,
            'message': 'Clock-out recorded successfully.' if created else 'Duplicate clock-out request recognized.'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class AttendanceSummaryListView(generics.ListAPIView):
    serializer_class = DailyAttendanceSummarySerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        qs = DailyAttendanceSummary.objects.filter(organization=self.request.organization).select_related('employee')

        # Role-based restriction: EMPLOYEE only sees own attendance
        if role == 'EMPLOYEE':
            emp = Employee.objects.filter(organization=self.request.organization, user=self.request.user).first()
            if not emp:
                return DailyAttendanceSummary.objects.none()
            qs = qs.filter(employee=emp)

        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(date=date_param)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        emp_param = self.request.query_params.get('employee')
        if emp_param and role in ['ORGANIZATION_OWNER', 'HR_ADMIN', 'PAYROLL_MANAGER']:
            qs = qs.filter(employee_id=emp_param)

        return qs

class AttendanceSummaryMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        today = timezone.now().date()
        summaries = DailyAttendanceSummary.objects.filter(organization=request.organization, date=today)
        total_active_emps = Employee.objects.filter(organization=request.organization, employment_status='ACTIVE').count()
        
        present_count = summaries.filter(status=AttendanceStatus.PRESENT).count()
        half_day_count = summaries.filter(status=AttendanceStatus.HALF_DAY).count()
        absent_count = summaries.filter(status=AttendanceStatus.ABSENT).count()
        late_count = summaries.filter(is_late=True).count()

        return Response({
            'date': today,
            'total_active_employees': total_active_emps,
            'present_count': present_count,
            'half_day_count': half_day_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'attendance_rate': round(((present_count + half_day_count * 0.5) / total_active_emps * 100), 1) if total_active_emps > 0 else 0
        })

class AttendanceCorrectionListCreateView(generics.ListCreateAPIView):
    serializer_class = AttendanceCorrectionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        role = self.request.organization_membership.role
        qs = AttendanceCorrection.objects.filter(organization=self.request.organization).select_related(
            'employee', 'summary', 'reviewed_by'
        )
        if role == 'EMPLOYEE':
            emp = Employee.objects.filter(organization=self.request.organization, user=self.request.user).first()
            if not emp:
                return AttendanceCorrection.objects.none()
            qs = qs.filter(employee=emp)
        return qs

    def perform_create(self, serializer):
        emp = Employee.objects.filter(organization=self.request.organization, user=self.request.user).first()
        if not emp:
            self.permission_denied(self.request, message="Employee profile required to request correction.")
        serializer.save(organization=self.request.organization, employee=emp)

class AttendanceCorrectionApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request, pk):
        correction = generics.get_object_or_404(
            AttendanceCorrection.objects.filter(organization=request.organization),
            pk=pk
        )
        updated = approve_attendance_correction(correction, request.user)
        return Response(AttendanceCorrectionSerializer(updated).data)

class AttendanceCorrectionRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request, pk):
        correction = generics.get_object_or_404(
            AttendanceCorrection.objects.filter(organization=request.organization),
            pk=pk
        )
        if correction.status != CorrectionStatus.PENDING:
            return Response({'error': {'message': 'Correction is already resolved.'}}, status=status.HTTP_400_BAD_REQUEST)
        
        correction.status = CorrectionStatus.REJECTED
        correction.reviewed_by = request.user
        correction.rejection_reason = request.data.get('rejection_reason', 'Rejected by administrator.')
        correction.save()
        return Response(AttendanceCorrectionSerializer(correction).data)
