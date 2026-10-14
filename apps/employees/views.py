from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from apps.common.permissions import IsTenantMember, IsOrganizationOwnerOrHR
from apps.employees.models import Employee, EmploymentStatus
from apps.employees.serializers import EmployeeSerializer, EmployeeDetailSerializer
from apps.employees.services import create_employee, import_employees_csv, export_employees_csv

class EmployeeListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EmployeeDetailSerializer
        return EmployeeSerializer

    def get_queryset(self):
        qs = Employee.objects.filter(organization=self.request.organization).select_related(
            'branch', 'department', 'reporting_manager'
        )
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_code__icontains=search) |
                Q(email__icontains=search)
            )
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(employment_status=status_param)

        branch_id = self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        dept_id = self.request.query_params.get('department')
        if dept_id:
            qs = qs.filter(department_id=dept_id)

        return qs

    def create(self, request, *args, **kwargs):
        if request.organization_membership.role not in ['ORGANIZATION_OWNER', 'HR_ADMIN']:
            return Response(
                {'error': {'message': 'Only Organization Owners and HR Admins can create employees.'}},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = EmployeeDetailSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        employee = create_employee(request.organization, serializer.validated_data)

        from apps.accounts.services import send_employee_invitation
        activation_url = None
        if employee.user and employee.email:
            try:
                activation_url, _, _ = send_employee_invitation(employee, request)
            except Exception:
                pass

        resp_data = EmployeeDetailSerializer(employee, context={'request': request}).data
        resp_data['activation_url'] = activation_url
        return Response(resp_data, status=status.HTTP_201_CREATED)

class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    serializer_class = EmployeeDetailSerializer

    def get_queryset(self):
        return Employee.objects.filter(organization=self.request.organization).select_related(
            'branch', 'department', 'reporting_manager'
        )

    def perform_destroy(self, instance):
        # Soft-delete by marking as Terminated/Resigned or soft_delete
        instance.employment_status = EmploymentStatus.TERMINATED
        instance.save(update_fields=['employment_status', 'updated_at'])

class EmployeeImportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationOwnerOrHR]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj or not file_obj.name.endswith('.csv'):
            return Response({'error': {'message': 'Please upload a valid .csv file.'}}, status=status.HTTP_400_BAD_REQUEST)

        result = import_employees_csv(request.organization, file_obj)
        if not result['success']:
            return Response({
                'success': False,
                'message': 'CSV validation errors found. No records were committed.',
                'errors': result['errors']
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'message': f"Successfully imported {result['imported_count']} employees."
        }, status=status.HTTP_201_CREATED)

class EmployeeExportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        csv_data = export_employees_csv(request.organization)
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employees_{request.organization.slug}.csv"'
        return response
