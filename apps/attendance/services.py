from django.db import transaction
from django.utils import timezone
from datetime import datetime, time, timedelta
from rest_framework.exceptions import ValidationError
from apps.attendance.models import (
    AttendanceEvent, AttendanceEventType, DailyAttendanceSummary,
    AttendanceStatus, AttendanceCorrection, CorrectionStatus
)
from apps.shifts.models import ShiftAssignment, ShiftTemplate

@transaction.atomic
def record_clock_in(organization, employee, idempotency_key, client_timestamp=None, source='WEB'):
    """
    Idempotent clock-in event recording with authoritative server timestamp.
    """
    # 1. Idempotency Check
    existing_event = AttendanceEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing_event:
        return existing_event, False

    now = timezone.now()
    today = now.date()

    # 2. Check if daily summary is locked by closed payroll
    summary, _ = DailyAttendanceSummary.objects.get_or_create(
        organization=organization,
        employee=employee,
        date=today,
        defaults={'status': AttendanceStatus.PRESENT}
    )
    if summary.is_locked:
        raise ValidationError({'detail': 'Attendance for this date is locked due to finalized payroll.'})

    # Check for duplicate open clock-in
    last_event = AttendanceEvent.objects.filter(
        organization=organization,
        employee=employee,
        server_timestamp__date=today
    ).order_by('-server_timestamp').first()

    if last_event and last_event.event_type == AttendanceEventType.CLOCK_IN:
        raise ValidationError({'detail': 'Employee is already clocked in for today.'})

    # 3. Create AttendanceEvent
    event = AttendanceEvent.objects.create(
        organization=organization,
        employee=employee,
        event_type=AttendanceEventType.CLOCK_IN,
        server_timestamp=now,
        client_timestamp=client_timestamp,
        idempotency_key=idempotency_key,
        source=source
    )

    # 4. Update Daily Attendance Summary
    if not summary.first_clock_in:
        summary.first_clock_in = now

    # Evaluate late arrival against assigned shift
    shift_assignment = ShiftAssignment.objects.filter(
        employee=employee,
        effective_from__lte=today
    ).order_by('-effective_from').first()

    if shift_assignment:
        shift = shift_assignment.shift_template
        # Convert shift start time to today's datetime
        shift_start_dt = timezone.make_aware(datetime.combine(today, shift.start_time))
        grace_limit = shift_start_dt + timedelta(minutes=shift.grace_period_minutes)
        if now > grace_limit:
            summary.is_late = True

    summary.save()
    return event, True

@transaction.atomic
def record_clock_out(organization, employee, idempotency_key, client_timestamp=None, source='WEB'):
    """
    Idempotent clock-out event recording and daily work summary calculation.
    """
    existing_event = AttendanceEvent.objects.filter(idempotency_key=idempotency_key).first()
    if existing_event:
        return existing_event, False

    now = timezone.now()
    today = now.date()

    summary, _ = DailyAttendanceSummary.objects.get_or_create(
        organization=organization,
        employee=employee,
        date=today,
        defaults={'status': AttendanceStatus.PRESENT}
    )
    if summary.is_locked:
        raise ValidationError({'detail': 'Attendance for this date is locked due to finalized payroll.'})

    # Verify open clock-in
    last_event = AttendanceEvent.objects.filter(
        organization=organization,
        employee=employee,
        server_timestamp__date=today
    ).order_by('-server_timestamp').first()

    if not last_event or last_event.event_type != AttendanceEventType.CLOCK_IN:
        raise ValidationError({'detail': 'Cannot clock out without an active clock-in.'})

    event = AttendanceEvent.objects.create(
        organization=organization,
        employee=employee,
        event_type=AttendanceEventType.CLOCK_OUT,
        server_timestamp=now,
        client_timestamp=client_timestamp,
        idempotency_key=idempotency_key,
        source=source
    )

    summary.last_clock_out = now

    # Calculate total worked minutes
    if summary.first_clock_in:
        delta = now - summary.first_clock_in
        total_minutes = int(delta.total_seconds() // 60)
        
        # Deduct break duration if worked over 5 hours
        break_mins = 60 if total_minutes >= 300 else 0
        net_worked_minutes = max(0, total_minutes - break_mins)

        summary.total_work_minutes = net_worked_minutes
        summary.break_minutes = break_mins

        # Determine status
        if net_worked_minutes >= 420: # 7+ hours
            summary.status = AttendanceStatus.PRESENT
        elif net_worked_minutes >= 240: # 4+ hours
            summary.status = AttendanceStatus.HALF_DAY
        else:
            summary.status = AttendanceStatus.HALF_DAY

        # Check overtime (e.g. over 8 hours = 480 mins)
        if net_worked_minutes > 480:
            summary.overtime_minutes = net_worked_minutes - 480

    summary.save()
    return event, True

@transaction.atomic
def approve_attendance_correction(correction, reviewer_user):
    """
    Approves regularization and re-computes daily attendance summary.
    """
    if correction.status != CorrectionStatus.PENDING:
        raise ValidationError({'detail': f'Correction is already {correction.status}.'})

    summary = correction.summary
    if summary.is_locked:
        raise ValidationError({'detail': 'Underlying attendance summary is locked.'})

    correction.status = CorrectionStatus.APPROVED
    correction.reviewed_by = reviewer_user
    correction.save()

    # Apply corrected timings
    summary.first_clock_in = correction.requested_clock_in
    summary.last_clock_out = correction.requested_clock_out
    
    delta = correction.requested_clock_out - correction.requested_clock_in
    total_minutes = int(delta.total_seconds() // 60)
    break_mins = 60 if total_minutes >= 300 else 0
    net_worked = max(0, total_minutes - break_mins)

    summary.total_work_minutes = net_worked
    summary.break_minutes = break_mins
    summary.status = AttendanceStatus.PRESENT if net_worked >= 420 else AttendanceStatus.HALF_DAY
    summary.is_late = False
    summary.save()

    return correction
