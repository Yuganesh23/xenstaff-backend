from decimal import Decimal
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.services import create_user_and_organization
from apps.employees.models import Employee, EmploymentStatus
from apps.employees.services import create_employee
from apps.organizations.models import Branch, Department

class TenantIsolationTests(TestCase):
    def setUp(self):
        # Organization 1 (Alpha Corp)
        self.user1, self.org1, self.mem1, self.token1 = create_user_and_organization(
            email='owner@alpha.com',
            password='Password123!',
            first_name='Alice',
            last_name='Alpha',
            company_name='Alpha Corp'
        )
        self.hq1 = Branch.objects.filter(organization=self.org1).first()
        self.dept1 = Department.objects.filter(organization=self.org1).first()

        self.emp1 = create_employee(self.org1, {
            'employee_code': 'ALP-001',
            'first_name': 'Bob',
            'last_name': 'Alpha',
            'email': 'bob@alpha.com',
            'joining_date': date(2026, 1, 1),
            'branch': self.hq1,
            'department': self.dept1,
            'designation': 'Software Engineer'
        })

        # Organization 2 (Beta Industries)
        self.user2, self.org2, self.mem2, self.token2 = create_user_and_organization(
            email='owner@beta.com',
            password='Password123!',
            first_name='Brian',
            last_name='Beta',
            company_name='Beta Industries'
        )
        self.hq2 = Branch.objects.filter(organization=self.org2).first()
        self.dept2 = Department.objects.filter(organization=self.org2).first()

        self.emp2 = create_employee(self.org2, {
            'employee_code': 'BET-001',
            'first_name': 'Brenda',
            'last_name': 'Beta',
            'email': 'brenda@beta.com',
            'joining_date': date(2026, 1, 1),
            'branch': self.hq2,
            'department': self.dept2,
            'designation': 'Product Lead'
        })

        self.client1 = APIClient()
        self.client1.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1.key}')

        self.client2 = APIClient()
        self.client2.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2.key}')

    def test_organization_1_cannot_see_organization_2_employees(self):
        """
        Verify tenant 1 listing employees does not include tenant 2's employees.
        """
        response = self.client1.get('/api/v1/employees/')
        self.assertEqual(response.status_code, 200)
        emp_codes = [emp['employee_code'] for emp in response.data['results']]
        self.assertIn('ALP-001', emp_codes)
        self.assertNotIn('BET-001', emp_codes)

    def test_organization_1_cannot_access_organization_2_employee_detail(self):
        """
        Verify direct lookup of Org 2's employee by Org 1 returns 404 Not Found.
        """
        response = self.client1.get(f'/api/v1/employees/{self.emp2.id}')
        self.assertEqual(response.status_code, 404)

    def test_organization_1_cannot_modify_organization_2_employee(self):
        """
        Verify attempt by Org 1 to patch Org 2's employee returns 404 Not Found.
        """
        response = self.client1.patch(f'/api/v1/employees/{self.emp2.id}', {
            'designation': 'Hacked Title'
        })
        self.assertEqual(response.status_code, 404)
        self.emp2.refresh_from_db()
        self.assertEqual(self.emp2.designation, 'Product Lead')

    def test_cross_tenant_branch_injection_prevented(self):
        """
        Attempting to assign Org 2's branch to an Org 1 employee fails or is blocked.
        """
        response = self.client1.post('/api/v1/employees/', {
            'employee_code': 'ALP-002',
            'first_name': 'Charlie',
            'email': 'charlie@alpha.com',
            'joining_date': '2026-02-01',
            'branch': str(self.hq2.id), # Org 2 branch!
            'department': str(self.dept1.id),
            'designation': 'QA Engineer'
        })
        # Serializer/database validation should block or reject foreign tenant relation
        self.assertNotEqual(response.status_code, 201)
