from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta, time
from decimal import Decimal
from apps.accounts.models import User, OrganizationMembership, OrganizationRole, AuthToken

@transaction.atomic
def create_user_and_organization(email, password, first_name, last_name, company_name):
    """
    Onboards a new organization owner with full defaults (branches, shifts, leaves, salary structure).
    """
    # 1. Create User
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name or ''
    )

    # 2. Create Organization
    from apps.organizations.models import Organization, Branch, Department
    base_slug = slugify(company_name) or 'company'
    slug = base_slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization.objects.create(
        name=company_name,
        legal_name=company_name,
        slug=slug,
        onboarding_step='INITIAL'
    )

    # 3. Create Membership as Organization Owner
    membership = OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=OrganizationRole.ORGANIZATION_OWNER
    )

    # 4. Create Default Headquarter Branch
    hq_branch = Branch.objects.create(
        organization=org,
        name='Headquarters',
        code='HQ-01',
        city='Chennai',
        state='Tamil Nadu',
        is_headquarters=True
    )

    # 5. Create Default Departments
    dept_eng = Department.objects.create(organization=org, name='Engineering', code='ENG')
    Department.objects.create(organization=org, name='Human Resources', code='HR')
    Department.objects.create(organization=org, name='Operations', code='OPS')

    # 6. Create Default General Shift
    from apps.shifts.models import ShiftTemplate
    ShiftTemplate.objects.create(
        organization=org,
        name='General Shift',
        start_time=time(9, 0),
        end_time=time(18, 0),
        grace_period_minutes=15,
        break_duration_minutes=60,
        working_hours=Decimal('8.00')
    )

    # 7. Create Default Leave Types
    from apps.leave_management.models import LeaveType
    LeaveType.objects.create(organization=org, name='Casual Leave', code='CL', annual_quota=Decimal('12.00'), is_paid=True)
    LeaveType.objects.create(organization=org, name='Sick Leave', code='SL', annual_quota=Decimal('12.00'), is_paid=True)
    LeaveType.objects.create(organization=org, name='Earned Leave', code='EL', annual_quota=Decimal('15.00'), is_paid=True)
    LeaveType.objects.create(organization=org, name='Leave Without Pay', code='LOP', annual_quota=Decimal('0.00'), is_paid=False)

    # 8. Create Default Salary Structure
    from apps.payroll.models import SalaryStructure, SalaryComponent
    struct = SalaryStructure.objects.create(
        organization=org,
        name='Standard Corporate Salary Structure',
        description='Standard Indian Corporate structure (Basic 50%, HRA 25%, Special Allowance 25%)'
    )
    SalaryComponent.objects.create(
        salary_structure=struct,
        name='Basic Salary',
        code='BASIC',
        component_type='EARNING',
        calculation_type='PERCENTAGE',
        amount_or_percentage=Decimal('50.00'),
        percentage_basis_code='CTC'
    )
    SalaryComponent.objects.create(
        salary_structure=struct,
        name='House Rent Allowance',
        code='HRA',
        component_type='EARNING',
        calculation_type='PERCENTAGE',
        amount_or_percentage=Decimal('50.00'),
        percentage_basis_code='BASIC'
    )
    SalaryComponent.objects.create(
        salary_structure=struct,
        name='Special Allowance',
        code='SPECIAL_ALLOWANCE',
        component_type='EARNING',
        calculation_type='PERCENTAGE',
        amount_or_percentage=Decimal('25.00'),
        percentage_basis_code='CTC'
    )

    # 9. Create 14-Day Free Trial Subscription
    from apps.subscriptions.models import Subscription, SubscriptionPlan
    starter_plan, _ = SubscriptionPlan.objects.get_or_create(
        code='STARTER',
        defaults={
            'name': 'Starter Plan',
            'monthly_price': Decimal('399.00'),
            'annual_price': Decimal('3990.00'),
            'max_employees': 10
        }
    )
    now = timezone.now()
    Subscription.objects.create(
        organization=org,
        plan=starter_plan,
        billing_interval='MONTHLY',
        status='TRIALING',
        current_period_start=now,
        current_period_end=now + timedelta(days=14)
    )

    # 10. Generate Auth Token
    token = AuthToken.objects.create(user=user)

    return user, org, membership, token


from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.exceptions import ValidationError


def generate_invitation_url(user, request=None):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return f"{base_url}/set-password?uid={uid}&token={token}", uid, token


def send_employee_invitation(employee, request=None):
    user = employee.user
    if not user or not user.email:
        raise ValidationError({"detail": "Employee does not have an email or user account."})

    url, uid, token = generate_invitation_url(user, request)
    org_name = employee.organization.name

    subject = f"Activate your {org_name} account on XenStaff"
    message = (
        f"Hi {employee.first_name},\n\n"
        f"You have been invited to join {org_name} on XenStaff.\n\n"
        f"Please click the link below to set your confidential password and activate your account:\n"
        f"{url}\n\n"
        f"This activation link is valid for 48 hours.\n\n"
        f"Best regards,\n"
        f"{org_name} Team"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )
    return url, uid, token


def verify_invitation_token(uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None, "Invalid activation link."

    if not default_token_generator.check_token(user, token):
        return None, "This activation link is invalid, expired, or has already been used."

    return user, None


@transaction.atomic
def set_employee_password(uidb64, token, password):
    user, error = verify_invitation_token(uidb64, token)
    if error:
        raise ValidationError({'token': error})

    user.set_password(password)
    user.is_active = True
    user.save()

    # Generate fresh auth token
    auth_token = AuthToken.objects.create(user=user)
    return user, auth_token
