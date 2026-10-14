from django.db.models import Count, Sum, Q
from apps.attendance.models import DailyAttendanceSummary, AttendanceStatus
from apps.leave_management.models import LeaveRequest, LeaveRequestStatus, LeaveBalance
from apps.payroll.models import PayrollRun, PayrollItem

def get_attendance_report(organization, start_date, end_date):
    """
    Aggregates attendance metrics across a date range.
    """
    qs = DailyAttendanceSummary.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=end_date
    )

    metrics = qs.aggregate(
        total_records=Count('id'),
        present_count=Count('id', filter=Q(status=AttendanceStatus.PRESENT)),
        half_day_count=Count('id', filter=Q(status=AttendanceStatus.HALF_DAY)),
        absent_count=Count('id', filter=Q(status=AttendanceStatus.ABSENT)),
        paid_leave_count=Count('id', filter=Q(status=AttendanceStatus.PAID_LEAVE)),
        unpaid_leave_count=Count('id', filter=Q(status=AttendanceStatus.UNPAID_LEAVE)),
        late_count=Count('id', filter=Q(is_late=True)),
        total_overtime_minutes=Sum('overtime_minutes')
    )

    return {
        'start_date': start_date,
        'end_date': end_date,
        'summary': metrics
    }

def get_leave_report(organization, year):
    """
    Aggregates employee leave quotas and utilization for an annual cycle.
    """
    balances = LeaveBalance.objects.filter(
        organization=organization,
        year=year
    ).values(
        'leave_type__name', 'leave_type__code'
    ).annotate(
        total_allocated=Sum('allocated_days'),
        total_used=Sum('used_days'),
        total_pending=Sum('pending_days')
    )

    return {
        'year': year,
        'balances_by_type': list(balances)
    }

def get_payroll_register(organization, payroll_run_id):
    """
    Retrieves full breakdown of a payroll run for audit registers.
    """
    run = PayrollRun.objects.filter(organization=organization, id=payroll_run_id).first()
    if not run:
        return None

    items = run.items.all().select_related('employee__department', 'employee__branch')
    return {
        'payroll_run': run,
        'items': items
    }
