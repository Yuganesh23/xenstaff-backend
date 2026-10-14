from decimal import Decimal
from datetime import date
from django.test import TestCase
from apps.accounts.services import create_user_and_organization
from apps.employees.services import create_employee
from apps.organizations.models import Branch, Department
from apps.attendance.models import DailyAttendanceSummary, AttendanceStatus
from apps.payroll.models import (
    SalaryStructure, SalaryComponent, EmployeeSalaryAssignment,
    PayrollRun, PayrollRunState
)
from apps.payroll.services.engine import (
    calculate_payroll_run, approve_payroll_run, publish_payroll_run, close_payroll_run
)

class PayrollEngineTests(TestCase):
    def setUp(self):
        self.user, self.org, self.membership, self.token = create_user_and_organization(
            email='founder@acme.com',
            password='Password123!',
            first_name='Frank',
            last_name='Founder',
            company_name='Acme Labs'
        )
        self.branch = Branch.objects.filter(organization=self.org).first()
        self.dept = Department.objects.filter(organization=self.org).first()

        # Create Standard Employee with ₹60,000 Monthly CTC
        self.emp = create_employee(self.org, {
            'employee_code': 'ACM-001',
            'first_name': 'Dev',
            'last_name': 'Tester',
            'email': 'dev@acme.com',
            'joining_date': date(2026, 1, 1),
            'branch': self.branch,
            'department': self.dept,
            'designation': 'Senior Developer'
        })

        # Set specific salary structure: Basic 50% (₹30,000), HRA 25% (₹15,000), Special 25% (₹15,000)
        self.structure = SalaryStructure.objects.create(
            organization=self.org,
            name='Test Structure'
        )
        SalaryComponent.objects.create(
            salary_structure=self.structure,
            name='Basic Salary',
            code='BASIC',
            component_type='EARNING',
            calculation_type='PERCENTAGE',
            amount_or_percentage=Decimal('50.00'),
            percentage_basis_code='CTC'
        )
        SalaryComponent.objects.create(
            salary_structure=self.structure,
            name='House Rent Allowance',
            code='HRA',
            component_type='EARNING',
            calculation_type='PERCENTAGE',
            amount_or_percentage=Decimal('25.00'),
            percentage_basis_code='CTC'
        )
        SalaryComponent.objects.create(
            salary_structure=self.structure,
            name='Special Allowance',
            code='SPECIAL_ALLOWANCE',
            component_type='EARNING',
            calculation_type='PERCENTAGE',
            amount_or_percentage=Decimal('25.00'),
            percentage_basis_code='CTC'
        )

        EmployeeSalaryAssignment.objects.filter(employee=self.emp).delete()
        self.assignment = EmployeeSalaryAssignment.objects.create(
            employee=self.emp,
            salary_structure=self.structure,
            monthly_ctc=Decimal('60000.00'),
            effective_from=date(2026, 1, 1)
        )

    def test_full_month_salary_no_deductions(self):
        """
        Verify that a full month (30 days) with no deductions yields exact gross CTC.
        """
        run = PayrollRun.objects.create(
            organization=self.org,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            month=4,
            year=2026,
            calculation_divisor_type='CALENDAR_DAYS'
        )
        calculate_payroll_run(run)
        run.refresh_from_db()

        item = run.items.get(employee=self.emp)
        self.assertEqual(item.payable_days, Decimal('30.00'))
        self.assertEqual(item.lop_days, Decimal('0.00'))
        self.assertEqual(item.gross_earnings, Decimal('60000.00'))
        self.assertEqual(item.total_deductions, Decimal('0.00'))
        self.assertEqual(item.net_salary, Decimal('60000.00'))

    def test_unpaid_leave_with_30_day_divisor(self):
        """
        Verify that 3 days of unpaid leave with 30-day divisor deducts 10% of CTC.
        Expected Net: 27 / 30 * 60,000 = ₹54,000.00
        """
        run = PayrollRun.objects.create(
            organization=self.org,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            month=4,
            year=2026,
            calculation_divisor_type='FIXED_30'
        )

        # Mark 3 days unpaid leave
        DailyAttendanceSummary.objects.create(
            organization=self.org,
            employee=self.emp,
            date=date(2026, 4, 10),
            status=AttendanceStatus.UNPAID_LEAVE
        )
        DailyAttendanceSummary.objects.create(
            organization=self.org,
            employee=self.emp,
            date=date(2026, 4, 11),
            status=AttendanceStatus.UNPAID_LEAVE
        )
        DailyAttendanceSummary.objects.create(
            organization=self.org,
            employee=self.emp,
            date=date(2026, 4, 12),
            status=AttendanceStatus.UNPAID_LEAVE
        )

        calculate_payroll_run(run)
        item = run.items.get(employee=self.emp)
        self.assertEqual(item.payable_days, Decimal('27.00'))
        self.assertEqual(item.lop_days, Decimal('3.00'))
        self.assertEqual(item.net_salary, Decimal('54000.00'))

    def test_overtime_calculation(self):
        """
        Verify approved overtime hours are calculated and added to gross pay.
        """
        run = PayrollRun.objects.create(
            organization=self.org,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            month=4,
            year=2026,
            calculation_divisor_type='CALENDAR_DAYS'
        )

        # Record 4 hours overtime (240 mins)
        DailyAttendanceSummary.objects.create(
            organization=self.org,
            employee=self.emp,
            date=date(2026, 4, 15),
            status=AttendanceStatus.PRESENT,
            overtime_minutes=240
        )

        calculate_payroll_run(run)
        item = run.items.get(employee=self.emp)
        self.assertEqual(item.overtime_hours, Decimal('4.00'))
        # Basic = 30,000, Divisor = 30, Hourly = 30000 / (30 * 8) = 125.
        # Overtime Pay = 125 * 4 * 1.5 = 750.
        # Gross = 60,000 + 750 = ₹60,750.00
        self.assertEqual(item.net_salary, Decimal('60750.00'))

    def test_repeated_calculation_idempotency(self):
        """
        Re-running calculation on a DRAFT/REVIEW run clears existing items and produces identical output without duplicates.
        """
        run = PayrollRun.objects.create(
            organization=self.org,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            month=4,
            year=2026,
            calculation_divisor_type='CALENDAR_DAYS'
        )
        calculate_payroll_run(run)
        self.assertEqual(run.items.count(), 1)

        # Run again
        calculate_payroll_run(run)
        self.assertEqual(run.items.count(), 1)
        self.assertEqual(run.items.first().net_salary, Decimal('60000.00'))

    def test_payroll_approval_and_publishing_workflow(self):
        """
        Verify transition: DRAFT -> CALCULATING -> REVIEW -> APPROVED -> PUBLISHED -> CLOSED.
        """
        run = PayrollRun.objects.create(
            organization=self.org,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            month=4,
            year=2026,
            calculation_divisor_type='CALENDAR_DAYS'
        )
        calculate_payroll_run(run)
        self.assertEqual(run.state, PayrollRunState.REVIEW)

        approve_payroll_run(run, self.user)
        self.assertEqual(run.state, PayrollRunState.APPROVED)
        self.assertIsNotNone(run.approved_at)

        publish_payroll_run(run)
        self.assertEqual(run.state, PayrollRunState.PUBLISHED)
        # Verify payslips created
        self.assertEqual(run.organization.payslips_payslip_related.count(), 1)

        close_payroll_run(run)
        self.assertEqual(run.state, PayrollRunState.CLOSED)
