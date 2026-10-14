from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from apps.leave_management.models import (
    LeaveType, LeaveBalance, LeaveRequest, LeaveRequestStatus, LeaveLedgerEntry
)
from apps.attendance.models import DailyAttendanceSummary, AttendanceStatus

@transaction.atomic
def submit_leave_request(organization, employee, leave_type, start_date, end_date, total_days, is_half_day=False, reason=""):
    """
    Submits a leave request with date validation and balance checks.
    """
    if start_date > end_date:
        raise ValidationError({'start_date': 'Start date must be on or before end date.'})

    # Check for overlapping requests
    overlapping = LeaveRequest.objects.filter(
        organization=organization,
        employee=employee,
        status__in=[LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]
    ).filter(
        Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
    )

    if overlapping.exists():
        raise ValidationError({'detail': 'An existing leave request overlaps with the requested dates.'})

    year = start_date.year
    balance, _ = LeaveBalance.objects.get_or_create(
        organization=organization,
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={'allocated_days': leave_type.annual_quota}
    )

    if leave_type.is_paid:
        if balance.available_days < total_days:
            raise ValidationError({'detail': f'Insufficient leave balance. Available: {balance.available_days}, Requested: {total_days}'})
        balance.pending_days += total_days
        balance.save()

    leave_req = LeaveRequest.objects.create(
        organization=organization,
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        is_half_day=is_half_day,
        reason=reason,
        status=LeaveRequestStatus.PENDING
    )

    return leave_req

@transaction.atomic
def approve_leave_request(request_obj, reviewer_user):
    """
    Approves leave request, adjusts ledger, and marks daily attendance records.
    """
    if request_obj.status != LeaveRequestStatus.PENDING:
        raise ValidationError({'detail': f'Cannot approve request that is already {request_obj.status}.'})

    year = request_obj.start_date.year
    balance = LeaveBalance.objects.filter(
        employee=request_obj.employee,
        leave_type=request_obj.leave_type,
        year=year
    ).first()

    if request_obj.leave_type.is_paid and balance:
        balance.pending_days = max(Decimal('0.00'), balance.pending_days - request_obj.total_days)
        balance.used_days += request_obj.total_days
        balance.save()

        LeaveLedgerEntry.objects.create(
            organization=request_obj.organization,
            employee=request_obj.employee,
            leave_type=request_obj.leave_type,
            transaction_type='DEBIT',
            days=request_obj.total_days,
            balance_after=balance.available_days,
            note=f"Approved leave from {request_obj.start_date} to {request_obj.end_date}"
        )

    request_obj.status = LeaveRequestStatus.APPROVED
    request_obj.reviewed_by = reviewer_user
    request_obj.save()

    # Update DailyAttendanceSummary for each day
    curr_date = request_obj.start_date
    status_to_set = AttendanceStatus.PAID_LEAVE if request_obj.leave_type.is_paid else AttendanceStatus.UNPAID_LEAVE
    while curr_date <= request_obj.end_date:
        summary, _ = DailyAttendanceSummary.objects.get_or_create(
            organization=request_obj.organization,
            employee=request_obj.employee,
            date=curr_date,
            defaults={'status': status_to_set}
        )
        if not summary.is_locked:
            summary.status = status_to_set
            summary.save()
        curr_date += timedelta(days=1)

    return request_obj

@transaction.atomic
def reject_leave_request(request_obj, reviewer_user, rejection_reason=""):
    """
    Rejects leave application and releases reserved pending days.
    """
    if request_obj.status != LeaveRequestStatus.PENDING:
        raise ValidationError({'detail': f'Cannot reject request that is already {request_obj.status}.'})

    year = request_obj.start_date.year
    balance = LeaveBalance.objects.filter(
        employee=request_obj.employee,
        leave_type=request_obj.leave_type,
        year=year
    ).first()

    if request_obj.leave_type.is_paid and balance:
        balance.pending_days = max(Decimal('0.00'), balance.pending_days - request_obj.total_days)
        balance.save()

    request_obj.status = LeaveRequestStatus.REJECTED
    request_obj.reviewed_by = reviewer_user
    request_obj.rejection_reason = rejection_reason
    request_obj.save()

    return request_obj

@transaction.atomic
def cancel_leave_request(request_obj, user):
    """
    Cancels a leave request and restores balances if needed.
    """
    if request_obj.status == LeaveRequestStatus.CANCELLED:
        return request_obj

    year = request_obj.start_date.year
    balance = LeaveBalance.objects.filter(
        employee=request_obj.employee,
        leave_type=request_obj.leave_type,
        year=year
    ).first()

    if request_obj.status == LeaveRequestStatus.PENDING and balance and request_obj.leave_type.is_paid:
        balance.pending_days = max(Decimal('0.00'), balance.pending_days - request_obj.total_days)
        balance.save()
    elif request_obj.status == LeaveRequestStatus.APPROVED and balance and request_obj.leave_type.is_paid:
        balance.used_days = max(Decimal('0.00'), balance.used_days - request_obj.total_days)
        balance.save()
        LeaveLedgerEntry.objects.create(
            organization=request_obj.organization,
            employee=request_obj.employee,
            leave_type=request_obj.leave_type,
            transaction_type='CREDIT',
            days=request_obj.total_days,
            balance_after=balance.available_days,
            note=f"Cancelled approved leave from {request_obj.start_date} to {request_obj.end_date}"
        )

    request_obj.status = LeaveRequestStatus.CANCELLED
    request_obj.save()
    return request_obj
