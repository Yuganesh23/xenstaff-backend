from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.common.utils import round_currency
from apps.employees.models import Employee, EmploymentStatus
from apps.attendance.models import DailyAttendanceSummary, AttendanceStatus
from apps.payroll.models import (
    PayrollRun, PayrollRunState, PayrollItem, PayrollCalculationLine,
    PayrollException, EmployeeSalaryAssignment
)

@transaction.atomic
def calculate_payroll_run(payroll_run):
    """
    Independent, deterministic payroll calculation engine.
    Computes proration, loss-of-pay, overtime, and statutory components.
    """
    if payroll_run.state in [PayrollRunState.APPROVED, PayrollRunState.PUBLISHED, PayrollRunState.CLOSED]:
        raise ValidationError({'detail': f'Cannot recalculate payroll run in {payroll_run.state} state.'})

    payroll_run.state = PayrollRunState.CALCULATING
    payroll_run.save(update_fields=['state'])

    # 1. Clear previous items, lines, and exceptions (Idempotent rerun)
    payroll_run.exceptions.all().delete()
    payroll_run.items.all().delete()

    org = payroll_run.organization
    p_start = payroll_run.period_start
    p_end = payroll_run.period_end
    calendar_days = (p_end - p_start).days + 1

    # Determine calculation divisor
    if payroll_run.calculation_divisor_type == 'FIXED_30':
        divisor = Decimal('30.00')
    elif payroll_run.calculation_divisor_type == 'ACTUAL_WORKING_DAYS':
        # Exclude Saturdays and Sundays from working days
        working_days = 0
        cur = p_start
        while cur <= p_end:
            if cur.weekday() < 5: # Monday to Friday
                working_days += 1
            cur += timedelta(days=1)
        divisor = Decimal(str(max(1, working_days)))
    else: # CALENDAR_DAYS default
        divisor = Decimal(str(calendar_days))

    employees = Employee.objects.filter(
        organization=org
    ).exclude(employment_status=EmploymentStatus.TERMINATED, exit_date__lt=p_start)

    total_gross_acc = Decimal('0.00')
    total_deductions_acc = Decimal('0.00')
    total_net_acc = Decimal('0.00')
    has_errors = False

    for emp in employees:
        # Check salary assignment
        assignment = EmployeeSalaryAssignment.objects.filter(
            employee=emp,
            effective_from__lte=p_end
        ).order_by('-effective_from').first()

        if not assignment:
            PayrollException.objects.create(
                payroll_run=payroll_run,
                employee=emp,
                exception_type='MISSING_SALARY_STRUCTURE',
                severity='ERROR',
                description=f"Employee {emp.employee_code} has no active salary assignment for this period."
            )
            has_errors = True
            continue

        # Calculate attendance factors (LOP and Overtime)
        summaries = DailyAttendanceSummary.objects.filter(
            employee=emp,
            date__gte=p_start,
            date__lte=p_end
        )

        lop_days = Decimal('0.00')
        overtime_hours = Decimal('0.00')

        for s in summaries:
            if s.status in [AttendanceStatus.UNPAID_LEAVE, AttendanceStatus.ABSENT]:
                lop_days += Decimal('1.00')
            elif s.status == AttendanceStatus.HALF_DAY:
                lop_days += Decimal('0.50')
            
            if s.overtime_minutes > 0:
                overtime_hours += Decimal(str(round(s.overtime_minutes / 60.0, 2)))

        # Handle Mid-Month Joining
        pre_joining_days = Decimal('0.00')
        if emp.joining_date > p_start:
            pre_joining_days = Decimal(str((emp.joining_date - p_start).days))

        # Handle Mid-Month Exit
        post_exit_days = Decimal('0.00')
        if emp.exit_date and emp.exit_date < p_end:
            post_exit_days = Decimal(str((p_end - emp.exit_date).days))

        # Calculate Payable Days
        payable_days = max(
            Decimal('0.00'),
            Decimal(str(calendar_days)) - lop_days - pre_joining_days - post_exit_days
        )

        # Ratio of payable days to divisor for pro-rating monthly components
        proration_factor = payable_days / divisor

        # Calculate earnings and deductions from structure components
        monthly_ctc = assignment.monthly_ctc
        structure = assignment.salary_structure
        components = structure.components.all()

        item_gross = Decimal('0.00')
        item_deductions = Decimal('0.00')
        lines_to_create = []

        basic_monthly = Decimal('0.00')
        # First pass: determine base amounts (especially BASIC for percentage deductions)
        for comp in components:
            if comp.code == 'BASIC':
                if comp.calculation_type == 'PERCENTAGE':
                    basic_monthly = round_currency(monthly_ctc * (comp.amount_or_percentage / Decimal('100.00')))
                else:
                    basic_monthly = comp.amount_or_percentage
                break
        
        if basic_monthly == Decimal('0.00'):
            basic_monthly = round_currency(monthly_ctc * Decimal('0.50')) # Fallback 50%

        # Second pass: compute lines
        for comp in components:
            if comp.component_type == 'EARNING':
                if comp.calculation_type == 'PERCENTAGE':
                    basis = monthly_ctc if comp.percentage_basis_code == 'CTC' else basic_monthly
                    base_amount = round_currency(basis * (comp.amount_or_percentage / Decimal('100.00')))
                else:
                    base_amount = comp.amount_or_percentage
                
                # Pro-rate earning
                calc_amount = round_currency(base_amount * proration_factor)
                item_gross += calc_amount

                lines_to_create.append({
                    'component_name': comp.name,
                    'component_code': comp.code,
                    'component_type': comp.component_type,
                    'base_amount': base_amount,
                    'calculated_amount': calc_amount,
                })
            else: # DEDUCTION
                if comp.calculation_type == 'PERCENTAGE':
                    basis = basic_monthly if comp.percentage_basis_code == 'BASIC' else monthly_ctc
                    base_amount = round_currency(basis * (comp.amount_or_percentage / Decimal('100.00')))
                else:
                    base_amount = comp.amount_or_percentage
                
                calc_amount = base_amount
                item_deductions += calc_amount

                lines_to_create.append({
                    'component_name': comp.name,
                    'component_code': comp.code,
                    'component_type': comp.component_type,
                    'base_amount': base_amount,
                    'calculated_amount': calc_amount,
                })

        # Add Overtime earning line if applicable
        if overtime_hours > Decimal('0.00'):
            hourly_rate = basic_monthly / (divisor * Decimal('8.00'))
            ot_amount = round_currency(hourly_rate * overtime_hours * Decimal('1.50'))
            item_gross += ot_amount
            lines_to_create.append({
                'component_name': 'Overtime Pay',
                'component_code': 'OVERTIME',
                'component_type': 'EARNING',
                'base_amount': ot_amount,
                'calculated_amount': ot_amount,
            })

        # Calculate Net Salary (Gross - Deductions, rounded to nearest rupee)
        raw_net = item_gross - item_deductions
        net_salary = round_currency(raw_net, 0) # Round to nearest Rupee

        if net_salary < Decimal('0.00'):
            PayrollException.objects.create(
                payroll_run=payroll_run,
                employee=emp,
                exception_type='NEGATIVE_NET_SALARY',
                severity='ERROR',
                description=f"Negative net salary (₹{net_salary}) computed for employee {emp.employee_code}. Total deductions exceed gross."
            )
            has_errors = True

        # Persist PayrollItem
        item = PayrollItem.objects.create(
            payroll_run=payroll_run,
            employee=emp,
            calendar_days=calendar_days,
            payable_days=payable_days,
            lop_days=lop_days,
            overtime_hours=overtime_hours,
            gross_earnings=item_gross,
            total_deductions=item_deductions,
            net_salary=net_salary
        )

        for line_data in lines_to_create:
            PayrollCalculationLine.objects.create(
                payroll_item=item,
                **line_data
            )

        total_gross_acc += item_gross
        total_deductions_acc += item_deductions
        total_net_acc += net_salary

    payroll_run.total_gross = total_gross_acc
    payroll_run.total_deductions = total_deductions_acc
    payroll_run.total_net = total_net_acc
    payroll_run.state = PayrollRunState.REVIEW
    payroll_run.save()

    return payroll_run

@transaction.atomic
def approve_payroll_run(payroll_run, user):
    """
    Transitions payroll run from REVIEW to APPROVED state.
    """
    if payroll_run.state != PayrollRunState.REVIEW:
        raise ValidationError({'detail': f'Cannot approve run in {payroll_run.state} state. Must be in REVIEW.'})

    unresolved_errors = payroll_run.exceptions.filter(severity='ERROR', is_resolved=False).count()
    if unresolved_errors > 0:
        raise ValidationError({'detail': f'Cannot approve run: {unresolved_errors} unresolved error exceptions exist.'})

    payroll_run.state = PayrollRunState.APPROVED
    payroll_run.approved_by = user
    payroll_run.approved_at = timezone.now()
    payroll_run.save()
    return payroll_run

@transaction.atomic
def publish_payroll_run(payroll_run):
    """
    Transitions run from APPROVED to PUBLISHED and creates Payslip records.
    """
    if payroll_run.state != PayrollRunState.APPROVED:
        raise ValidationError({'detail': f'Cannot publish run in {payroll_run.state} state. Must be APPROVED.'})

    payroll_run.state = PayrollRunState.PUBLISHED
    payroll_run.save()

    from apps.payslips.models import Payslip
    now = timezone.now()
    for item in payroll_run.items.all():
        number = f"PAY-{payroll_run.year}{payroll_run.month:02d}-{item.employee.employee_code}"
        payslip, _ = Payslip.objects.get_or_create(
            organization=payroll_run.organization,
            payroll_item=item,
            defaults={
                'payslip_number': number,
                'is_published': True,
                'published_at': now
            }
        )
        payslip.is_published = True
        payslip.published_at = now
        payslip.save()

    return payroll_run

@transaction.atomic
def close_payroll_run(payroll_run):
    """
    Transitions run to CLOSED and locks attendance records for the period.
    """
    if payroll_run.state != PayrollRunState.PUBLISHED:
        raise ValidationError({'detail': f'Cannot close run in {payroll_run.state} state. Must be PUBLISHED.'})

    payroll_run.state = PayrollRunState.CLOSED
    payroll_run.save()

    # Lock attendance summaries
    DailyAttendanceSummary.objects.filter(
        organization=payroll_run.organization,
        date__gte=payroll_run.period_start,
        date__lte=payroll_run.period_end
    ).update(is_locked=True)

    return payroll_run

@transaction.atomic
def revise_payroll_run(payroll_run, user):
    """
    Creates an authorized revision / adjustment cycle.
    """
    if payroll_run.state not in [PayrollRunState.APPROVED, PayrollRunState.PUBLISHED, PayrollRunState.CLOSED]:
        raise ValidationError({'detail': 'Can only revise approved, published, or closed runs.'})

    payroll_run.state = PayrollRunState.DRAFT
    payroll_run.save()
    return calculate_payroll_run(payroll_run)
