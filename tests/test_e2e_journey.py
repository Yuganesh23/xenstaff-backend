import uuid
from decimal import Decimal
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User, AuthToken
from apps.organizations.models import Branch, Department
from apps.shifts.models import ShiftTemplate, ShiftAssignment
from apps.leave_management.models import LeaveType, LeaveRequest
from apps.payroll.models import SalaryStructure, SalaryComponent, EmployeeSalaryAssignment, PayrollRun
from apps.payslips.models import Payslip

class EndToEndJourneyTests(TestCase):
    def test_complete_business_lifecycle(self):
        client = APIClient()

        # Step 1: Register an Organization
        reg_response = client.post('/api/v1/auth/register', {
            'email': 'ceo@megacorp.in',
            'password': 'StrongPassword2026!',
            'first_name': 'Ramesh',
            'last_name': 'Kumar',
            'company_name': 'MegaCorp Technologies'
        })
        self.assertEqual(reg_response.status_code, 201)
        owner_token = reg_response.data['token']
        org_id = reg_response.data['organization']['id']

        client.credentials(HTTP_AUTHORIZATION=f'Bearer {owner_token}', HTTP_X_ORGANIZATION_ID=org_id)

        # Step 2: Complete Initial Setup / Inspect current organization
        org_res = client.get('/api/v1/organizations/current')
        self.assertEqual(org_res.status_code, 200)

        branch_res = client.get('/api/v1/organizations/branches')
        self.assertEqual(branch_res.status_code, 200)
        branch_id = branch_res.data['results'][0]['id']

        dept_res = client.get('/api/v1/organizations/departments')
        self.assertEqual(dept_res.status_code, 200)
        dept_id = dept_res.data['results'][0]['id']

        # Step 3: Add an Employee
        emp_res = client.post('/api/v1/employees/', {
            'employee_code': 'MC-001',
            'first_name': 'Suresh',
            'last_name': 'Raina',
            'email': 'suresh@megacorp.in',
            'joining_date': '2026-04-01',
            'branch': branch_id,
            'department': dept_id,
            'designation': 'Senior Systems Architect',
            'bank_account_number': '98765432101234',
            'bank_ifsc': 'HDFC0001234',
            'bank_name': 'HDFC Bank'
        })
        self.assertEqual(emp_res.status_code, 201)
        emp_id = emp_res.data['id']

        # Step 4: Shift is automatically assigned (or explicitly verified)
        shift_res = client.get('/api/v1/shifts/')
        self.assertEqual(shift_res.status_code, 200)

        # Step 5: Record Attendance (Clock In & Clock Out)
        in_key = f"punch_in_{uuid.uuid4().hex}"
        cin_res = client.post('/api/v1/attendance/clock-in', {
            'employee_id': emp_id,
            'idempotency_key': in_key,
            'source': 'PWA'
        })
        self.assertEqual(cin_res.status_code, 201)

        out_key = f"punch_out_{uuid.uuid4().hex}"
        cout_res = client.post('/api/v1/attendance/clock-out', {
            'employee_id': emp_id,
            'idempotency_key': out_key,
            'source': 'PWA'
        })
        self.assertEqual(cout_res.status_code, 201)

        # Step 6: Submit and Approve a Leave Request
        leave_types = client.get('/api/v1/leave/types')
        self.assertEqual(leave_types.status_code, 200)
        cl_type_id = leave_types.data['results'][0]['id']

        leave_app = client.post('/api/v1/leave/requests', {
            'employee': emp_id,
            'leave_type': cl_type_id,
            'start_date': '2026-04-20',
            'end_date': '2026-04-21',
            'total_days': 2.0,
            'reason': 'Family function'
        })
        self.assertEqual(leave_app.status_code, 201)
        leave_id = leave_app.data['id']

        appr_leave = client.post(f'/api/v1/leave/requests/{leave_id}/approve')
        self.assertEqual(appr_leave.status_code, 200)
        self.assertEqual(appr_leave.data['status'], 'APPROVED')

        # Step 7: Configure Salary Structure & Assignment
        struct_res = client.get('/api/v1/payroll/salary-structures')
        self.assertEqual(struct_res.status_code, 200)

        # Step 8: Create and Calculate Payroll Run
        run_res = client.post('/api/v1/payroll/runs', {
            'period_start': '2026-04-01',
            'period_end': '2026-04-30',
            'month': 4,
            'year': 2026,
            'calculation_divisor_type': 'CALENDAR_DAYS'
        })
        self.assertEqual(run_res.status_code, 201)
        run_id = run_res.data['id']

        calc_res = client.post(f'/api/v1/payroll/runs/{run_id}/calculate')
        self.assertEqual(calc_res.status_code, 200)
        self.assertEqual(calc_res.data['state'], 'REVIEW')

        # Step 9: Review Exceptions (clean run -> 0 exceptions)
        exc_res = client.get(f'/api/v1/payroll/runs/{run_id}/exceptions')
        self.assertEqual(exc_res.status_code, 200)

        # Step 10: Approve Payroll
        appr_payroll = client.post(f'/api/v1/payroll/runs/{run_id}/approve')
        self.assertEqual(appr_payroll.status_code, 200)
        self.assertEqual(appr_payroll.data['state'], 'APPROVED')

        # Step 11: Publish Payslips
        pub_res = client.post(f'/api/v1/payroll/runs/{run_id}/publish')
        self.assertEqual(pub_res.status_code, 200)
        self.assertEqual(pub_res.data['state'], 'PUBLISHED')

        # Step 12: Sign in as Employee and download authentic PDF payslip
        emp_user = User.objects.get(email='suresh@megacorp.in')
        emp_token, _ = AuthToken.objects.get_or_create(user=emp_user)

        emp_client = APIClient()
        emp_client.credentials(HTTP_AUTHORIZATION=f'Bearer {emp_token.key}', HTTP_X_ORGANIZATION_ID=org_id)

        # Employee accesses their own payslip
        my_payslips = emp_client.get('/api/v1/payslips/')
        self.assertEqual(my_payslips.status_code, 200)
        self.assertEqual(my_payslips.data['count'], 1)
        payslip_id = my_payslips.data['results'][0]['id']

        # Download PDF payslip
        pdf_res = emp_client.get(f'/api/v1/payslips/{payslip_id}/download')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res['Content-Type'], 'application/pdf')
        self.assertTrue(pdf_res.content.startswith(b'%PDF'))
