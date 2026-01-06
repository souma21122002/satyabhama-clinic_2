from datetime import datetime, date, timedelta
from flask_mail import Message
from app.database import db
from app.models.appointment import Appointment

def send_appointment_reminders(mail, app):
    """Send email reminders for appointments happening tomorrow"""
    with app.app_context():
        tomorrow = date.today() + timedelta(days=1)
        
        appointments = Appointment.query.filter(
            Appointment.appointment_date == tomorrow,
            Appointment.status == 'scheduled',
            Appointment.reminder_sent == False
        ).all()
        
        for appointment in appointments:
            try:
                # Send to patient
                if hasattr(appointment.patient, 'email') and appointment.patient.email:
                    msg = Message(
                        subject='Appointment Reminder - Homeopathy Clinic',
                        recipients=[appointment.patient.email],
                        html=f'''
                        <h2>Appointment Reminder</h2>
                        <p>Dear {appointment.patient.name if hasattr(appointment.patient, 'name') else 'Patient'},</p>
                        <p>This is a reminder for your upcoming appointment:</p>
                        <ul>
                            <li><strong>Date:</strong> {appointment.appointment_date.strftime('%B %d, %Y')}</li>
                            <li><strong>Time:</strong> {appointment.appointment_time.strftime('%I:%M %p')}</li>
                            <li><strong>Doctor:</strong> Dr. {appointment.doctor.name if hasattr(appointment.doctor, 'name') else 'Doctor'}</li>
                        </ul>
                        <p>Please arrive 10 minutes before your scheduled time.</p>
                        <p>If you need to cancel or reschedule, please do so at least 24 hours in advance.</p>
                        <br>
                        <p>Best regards,<br>Homeopathy Clinic</p>
                        '''
                    )
                    mail.send(msg)
                
                appointment.reminder_sent = True
                db.session.commit()
                
            except Exception as e:
                print(f"Failed to send reminder for appointment {appointment.id}: {e}")

def send_confirmation_email(mail, appointment):
    """Send confirmation email when appointment is booked"""
    try:
        if hasattr(appointment.patient, 'email') and appointment.patient.email:
            msg = Message(
                subject='Appointment Confirmed - Homeopathy Clinic',
                recipients=[appointment.patient.email],
                html=f'''
                <h2>Appointment Confirmed</h2>
                <p>Dear {appointment.patient.name if hasattr(appointment.patient, 'name') else 'Patient'},</p>
                <p>Your appointment has been confirmed:</p>
                <ul>
                    <li><strong>Date:</strong> {appointment.appointment_date.strftime('%B %d, %Y')}</li>
                    <li><strong>Time:</strong> {appointment.appointment_time.strftime('%I:%M %p')}</li>
                    <li><strong>Doctor:</strong> Dr. {appointment.doctor.name if hasattr(appointment.doctor, 'name') else 'Doctor'}</li>
                </ul>
                <p>We will send you a reminder 24 hours before your appointment.</p>
                <br>
                <p>Best regards,<br>Homeopathy Clinic</p>
                '''
            )
            mail.send(msg)
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
