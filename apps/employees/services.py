import csv
import io
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.employees.models import Employee, EmploymentStatus, EmploymentType
from apps.organizations.models import Branch, Department
from apps.accounts.models import User, OrganizationMembership, OrganizationRole
from apps.subscriptions.services import enforce_seat_limit

@transaction.atomic
def create_employee(organization, data, create_user_account=True):
    """
    Creates an employee within an organization after enforcing seat limit quotas.
    """
    # 1. Enforce subscription seat limit
    enforce_seat_limit(organization)

    # 2. Check duplicate employee_code
    code = data.get('employee_code', '').strip().upper()
    if Employee.objects.filter(organization=organization, employee_code=code).exists():
        raise ValidationError({'employee_code': f"Employee code '{code}' already exists in this organization."})

    # 3. Handle user account creation if requested
    email = data.get('email', '').strip().lower()
    user = None
    if create_user_account and email:
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(
                email=email,
                first_name=data.get('first_name'),
                last_name=data.get('last_name', ''),
                password=data.get('password')
            )
        # Ensure membership
        OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={'role': OrganizationRole.EMPLOYEE}
        )

    # 4. Create Employee record
    employee = Employee.objects.create(
        organization=organization,
        user=user,
        employee_code=code,
        first_name=data.get('first_name'),
        last_name=data.get('last_name', ''),
        email=email,
        phone=data.get('phone', ''),
        date_of_birth=data.get('date_of_birth'),
        gender=data.get('gender', ''),
        joining_date=data.get('joining_date'),
        employment_status=data.get('employment_status', EmploymentStatus.ACTIVE),
        employment_type=data.get('employment_type', EmploymentType.FULL_TIME),
        branch=data.get('branch'),
        department=data.get('department'),
        designation=data.get('designation'),
        reporting_manager=data.get('reporting_manager'),
        pan_number=data.get('pan_number', ''),
        aadhaar_last_four=data.get('aadhaar_last_four', ''),
        bank_account_number=data.get('bank_account_number', ''),
        bank_ifsc=data.get('bank_ifsc', ''),
        bank_name=data.get('bank_name', '')
    )

    # 5. Automatically assign default General Shift and default Salary Structure if available
    from apps.shifts.models import ShiftTemplate, ShiftAssignment
    default_shift = ShiftTemplate.objects.filter(organization=organization).first()
    if default_shift:
        ShiftAssignment.objects.create(
            employee=employee,
            shift_template=default_shift,
            effective_from=employee.joining_date
        )

    from apps.payroll.models import SalaryStructure, EmployeeSalaryAssignment
    default_struct = SalaryStructure.objects.filter(organization=organization).first()
    if default_struct:
        from decimal import Decimal
        EmployeeSalaryAssignment.objects.create(
            employee=employee,
            salary_structure=default_struct,
            monthly_ctc=Decimal('35000.00'),
            effective_from=employee.joining_date
        )

    return employee

@transaction.atomic
def import_employees_csv(organization, csv_file):
    """
    Parses, validates, and imports employee records from CSV.
    """
    decoded_file = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded_file))
    
    branches = {b.code.upper(): b for b in Branch.objects.filter(organization=organization)}
    departments = {d.code.upper(): d for d in Department.objects.filter(organization=organization)}

    errors = []
    rows_to_create = []

    for idx, row in enumerate(reader, start=2): # line 1 is header
        row_errors = {}
        code = row.get('employee_code', '').strip().upper()
        if not code:
            row_errors['employee_code'] = 'Employee code is required.'
        elif Employee.objects.filter(organization=organization, employee_code=code).exists():
            row_errors['employee_code'] = f"Employee code {code} already exists."

        branch_code = row.get('branch_code', '').strip().upper()
        branch = branches.get(branch_code)
        if not branch:
            row_errors['branch_code'] = f"Branch code '{branch_code}' not found."

        dept_code = row.get('department_code', '').strip().upper()
        department = departments.get(dept_code)
        if not department:
            row_errors['department_code'] = f"Department code '{dept_code}' not found."

        first_name = row.get('first_name', '').strip()
        if not first_name:
            row_errors['first_name'] = 'First name is required.'

        email = row.get('email', '').strip().lower()
        if not email:
            row_errors['email'] = 'Email is required.'

        joining_date = row.get('joining_date', '').strip()
        if not joining_date:
            row_errors['joining_date'] = 'Joining date is required (YYYY-MM-DD).'

        if row_errors:
            errors.append({'row': idx, 'errors': row_errors})
        else:
            rows_to_create.append({
                'employee_code': code,
                'first_name': first_name,
                'last_name': row.get('last_name', '').strip(),
                'email': email,
                'phone': row.get('phone', '').strip(),
                'joining_date': joining_date,
                'branch': branch,
                'department': department,
                'designation': row.get('designation', '').strip() or 'Staff',
                'employment_type': row.get('employment_type', 'FULL_TIME').strip().upper()
            })

    if errors:
        return {'success': False, 'errors': errors, 'imported_count': 0}

    imported = []
    for item in rows_to_create:
        emp = create_employee(organization, item, create_user_account=True)
        imported.append(emp)

    return {'success': True, 'errors': [], 'imported_count': len(imported)}

def export_employees_csv(organization):
    """
    Exports all employees for an organization as CSV string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'employee_code', 'first_name', 'last_name', 'email', 'phone',
        'joining_date', 'employment_status', 'employment_type',
        'branch_code', 'branch_name', 'department_code', 'department_name', 'designation'
    ])
    
    employees = Employee.objects.filter(organization=organization).select_related('branch', 'department')
    for emp in employees:
        writer.writerow([
            emp.employee_code, emp.first_name, emp.last_name, emp.email, emp.phone,
            emp.joining_date, emp.employment_status, emp.employment_type,
            emp.branch.code, emp.branch.name, emp.department.code, emp.department.name, emp.designation
        ])
    
    return output.getvalue()
