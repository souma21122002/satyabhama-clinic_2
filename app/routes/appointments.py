from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date, time, timedelta
from app.database import db
from app.models.appointment import Appointment, DoctorAvailability
from app.models.user import User
from functools import wraps

appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'doctor':
            flash('Access denied. Doctor privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Patient: Book appointment
@appointments_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    doctors = User.query.filter_by(role='doctor').all()
    
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        reason = request.form.get('reason')
        
        if not all([doctor_id, appointment_date, appointment_time]):
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('appointments.book_appointment'))
        
        # Parse date and time
        appt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        appt_time = datetime.strptime(appointment_time, '%H:%M').time()
        
        # Check if slot is available
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='scheduled'
        ).first()
        
        if existing:
            flash('This time slot is already booked. Please choose another.', 'danger')
            return redirect(url_for('appointments.book_appointment'))
        
        # Create appointment
        appointment = Appointment(
            patient_id=session['user_id'],
            doctor_id=doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            reason=reason
        )
        db.session.add(appointment)
        db.session.commit()
        
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments.my_appointments'))
    
    return render_template('appointments/book.html', doctors=doctors)

# Get available slots for a doctor on a specific date
@appointments_bp.route('/available-slots/<int:doctor_id>/<date_str>')
@login_required
def get_available_slots(doctor_id, date_str):
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    if selected_date < date.today():
        return jsonify({'slots': []})
    
    day_of_week = selected_date.weekday()
    
    # Get doctor's availability for this day
    availability = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        day_of_week=day_of_week,
        is_active=True
    ).first()
    
    if not availability:
        return jsonify({'slots': []})
    
    # Generate time slots
    slots = []
    current_time = datetime.combine(selected_date, availability.start_time)
    end_time = datetime.combine(selected_date, availability.end_time)
    
    while current_time < end_time:
        slot_time = current_time.time()
        
        # Check if slot is already booked
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=selected_date,
            appointment_time=slot_time,
            status='scheduled'
        ).first()
        
        # Don't show past slots for today
        if selected_date == date.today() and slot_time <= datetime.now().time():
            current_time += timedelta(minutes=availability.slot_duration)
            continue
        
        if not existing:
            slots.append(slot_time.strftime('%H:%M'))
        
        current_time += timedelta(minutes=availability.slot_duration)
    
    return jsonify({'slots': slots})

# Patient: View my appointments
@appointments_bp.route('/my-appointments')
@login_required
def my_appointments():
    upcoming = Appointment.query.filter(
        Appointment.patient_id == session['user_id'],
        Appointment.appointment_date >= date.today(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    past = Appointment.query.filter(
        Appointment.patient_id == session['user_id'],
        (Appointment.appointment_date < date.today()) | (Appointment.status != 'scheduled')
    ).order_by(Appointment.appointment_date.desc()).limit(20).all()
    
    return render_template('appointments/my_appointments.html', upcoming=upcoming, past=past)

# Cancel appointment
@appointments_bp.route('/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check permission
    if appointment.patient_id != session['user_id'] and session.get('role') != 'doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('appointments.my_appointments'))
    
    cancellation_reason = request.form.get('cancellation_reason', '')
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = cancellation_reason
    db.session.commit()
    
    flash('Appointment cancelled successfully.', 'success')
    
    if session.get('role') == 'doctor':
        return redirect(url_for('appointments.doctor_calendar'))
    return redirect(url_for('appointments.my_appointments'))

# Reschedule appointment
@appointments_bp.route('/reschedule/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check permission
    if appointment.patient_id != session['user_id'] and session.get('role') != 'doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('appointments.my_appointments'))
    
    if request.method == 'POST':
        new_date = request.form.get('appointment_date')
        new_time = request.form.get('appointment_time')
        
        appt_date = datetime.strptime(new_date, '%Y-%m-%d').date()
        appt_time = datetime.strptime(new_time, '%H:%M').time()
        
        # Check if new slot is available
        existing = Appointment.query.filter_by(
            doctor_id=appointment.doctor_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status='scheduled'
        ).first()
        
        if existing and existing.id != appointment.id:
            flash('This time slot is already booked.', 'danger')
            return redirect(url_for('appointments.reschedule_appointment', appointment_id=appointment_id))
        
        appointment.appointment_date = appt_date
        appointment.appointment_time = appt_time
        appointment.status = 'scheduled'
        db.session.commit()
        
        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('appointments.my_appointments'))
    
    return render_template('appointments/reschedule.html', appointment=appointment)

# Doctor: Calendar view
@appointments_bp.route('/doctor/calendar')
@login_required
@doctor_required
def doctor_calendar():
    return render_template('appointments/doctor_calendar.html')

# Doctor: Get appointments for calendar
@appointments_bp.route('/doctor/appointments-data')
@login_required
@doctor_required
def doctor_appointments_data():
    start = request.args.get('start')
    end = request.args.get('end')
    
    appointments = Appointment.query.filter(
        Appointment.doctor_id == session['user_id'],
        Appointment.status == 'scheduled'
    ).all()
    
    events = []
    for appt in appointments:
        events.append({
            'id': appt.id,
            'title': f'{appt.patient.name if hasattr(appt.patient, "name") else "Patient"}',
            'start': f'{appt.appointment_date}T{appt.appointment_time}',
            'end': f'{appt.appointment_date}T{(datetime.combine(date.today(), appt.appointment_time) + timedelta(minutes=appt.duration)).time()}',
            'extendedProps': {
                'reason': appt.reason,
                'patient_id': appt.patient_id
            }
        })
    
    return jsonify(events)

# Doctor: Manage availability
@appointments_bp.route('/doctor/availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def manage_availability():
    if request.method == 'POST':
        # Clear existing availability
        DoctorAvailability.query.filter_by(doctor_id=session['user_id']).delete()
        
        days = request.form.getlist('days[]')
        start_times = request.form.getlist('start_times[]')
        end_times = request.form.getlist('end_times[]')
        slot_duration = int(request.form.get('slot_duration', 30))
        
        for i, day in enumerate(days):
            if start_times[i] and end_times[i]:
                availability = DoctorAvailability(
                    doctor_id=session['user_id'],
                    day_of_week=int(day),
                    start_time=datetime.strptime(start_times[i], '%H:%M').time(),
                    end_time=datetime.strptime(end_times[i], '%H:%M').time(),
                    slot_duration=slot_duration
                )
                db.session.add(availability)
        
        db.session.commit()
        flash('Availability updated successfully!', 'success')
        return redirect(url_for('appointments.manage_availability'))
    
    availabilities = DoctorAvailability.query.filter_by(
        doctor_id=session['user_id'],
        is_active=True
    ).order_by(DoctorAvailability.day_of_week).all()
    
    return render_template('appointments/availability.html', availabilities=availabilities)

# Doctor: View appointment details
@appointments_bp.route('/doctor/appointment/<int:appointment_id>')
@login_required
@doctor_required
def appointment_details(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('appointments.doctor_calendar'))
    
    return render_template('appointments/appointment_details.html', appointment=appointment)

# Doctor: Mark appointment as completed
@appointments_bp.route('/doctor/complete/<int:appointment_id>', methods=['POST'])
@login_required
@doctor_required
def complete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.doctor_id != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('appointments.doctor_calendar'))
    
    appointment.status = 'completed'
    appointment.notes = request.form.get('notes', '')
    db.session.commit()
    
    flash('Appointment marked as completed.', 'success')
    return redirect(url_for('appointments.doctor_calendar'))
