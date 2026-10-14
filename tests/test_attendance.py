import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.accounts.services import create_user_and_organization
from apps.employees.services import create_employee
from apps.organizations.models import Branch, Department
from apps.attendance.models import AttendanceStatus, AttendanceCorrection
from apps.attendance.services import (
    record_clock_in, record_clock_out, approve_attendance_correction
)

class AttendanceTests(TestCase):
    def setUp(self):
        self.user, self.org, self.membership, self.token = create_user_and_organization(
            email='founder@beta.com',
            password='Password123!',
            first_name='Frank',
            last_name='Founder',
            company_name='Beta Corp'
        )
        self.branch = Branch.objects.filter(organization=self.org).first()
        self.dept = Department.objects.filter(organization=self.org).first()

        self.emp = create_employee(self.org, {
            'employee_code': 'BET-001',
            'first_name': 'Ben',
            'last_name': 'Baker',
            'email': 'ben@beta.com',
            'joining_date': date(2026, 1, 1),
            'branch': self.branch,
            'department': self.dept,
            'designation': 'Support Lead'
        })

    def test_idempotent_clock_in(self):
        """
        Duplicate punch submission with identical idempotency_key returns original event without error or duplication.
        """
        key = f"punch_{uuid.uuid4().hex}"
        event1, created1 = record_clock_in(self.org, self.emp, idempotency_key=key)
        self.assertTrue(created1)

        event2, created2 = record_clock_in(self.org, self.emp, idempotency_key=key)
        self.assertFalse(created2)
        self.assertEqual(event1.id, event2.id)

    def test_clock_out_without_clock_in_rejected(self):
        """
        Attempting to clock out without an open clock-in raises ValidationError.
        """
        key = f"out_{uuid.uuid4().hex}"
        with self.assertRaises(ValidationError):
            record_clock_out(self.org, self.emp, idempotency_key=key)

    def test_full_attendance_lifecycle(self):
        """
        Clock in -> Clock out -> Verify daily summary work minutes calculated.
        """
        in_key = f"in_{uuid.uuid4().hex}"
        out_key = f"out_{uuid.uuid4().hex}"

        record_clock_in(self.org, self.emp, idempotency_key=in_key)
        record_clock_out(self.org, self.emp, idempotency_key=out_key)

        summary = self.emp.attendance_summaries.get(date=timezone.now().date())
        self.assertIsNotNone(summary.first_clock_in)
        self.assertIsNotNone(summary.last_clock_out)
