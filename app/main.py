import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from app.ai_matcher import AIRemedyMatcher

# Use appropriate database based on environment
if os.getenv("FLASK_ENV") == "production":
    from app.database import (
        init_db, save_case, load_all_cases, save_consultation, load_consultations,
        load_patient_consultations, save_user, get_user, load_all_patients,
        update_consultation_reply, delete_consultation_media, get_patient_history,
        update_patient_notes, get_user_by_id, get_all_doctors, save_doctor_availability,
        get_doctor_availability, get_availability_for_day, save_appointment,
        get_appointment, get_appointments_for_slot, get_patient_appointments,
        get_doctor_appointments, update_appointment_status, reschedule_appointment,
        update_appointment_notes, get_slot_booking_count, get_availability_for_date, delete_doctor_availability
    )
else:
    from app.database_local import (
        init_db, save_case, load_all_cases, save_consultation, load_consultations,
        load_patient_consultations, save_user, get_user, load_all_patients,
        update_consultation_reply, delete_consultation_media, get_patient_history,
        update_patient_notes, get_user_by_id, get_all_doctors, save_doctor_availability,
        get_doctor_availability, get_availability_for_day, save_appointment,
        get_appointment, get_appointments_for_slot, get_patient_appointments,
        get_doctor_appointments, update_appointment_status, reschedule_appointment,
        update_appointment_notes, get_slot_booking_count, get_availability_for_date, delete_doctor_availability
    )

from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "homeopathy-secret-key-2024")

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_AUDIO = {'webm', 'mp3', 'wav', 'ogg', 'm4a'}
ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

try:
    init_db()
    print("✅ Database initialized")
    
    doctor_email = "doctor@homeopathy.com"
    if not get_user(doctor_email):
        doctor_data = {
            "name": "Dr. Ajoy Kumar Singha Mahapatra",
            "email": doctor_email,
            "password": "doctor123",
            "phone": "+919932199936",
            "age": 35,
            "gender": "male",
            "role": "doctor"
        }
        save_user(doctor_data)
        print(f"✅ Default doctor account created: {doctor_email}")
    else:
        print(f"✅ Doctor account already exists: {doctor_email}")
except Exception as e:
    print(f"⚠️ Startup warning: {e}")

matcher = AIRemedyMatcher()

# Production settings
if os.getenv("FLASK_ENV") == "production":
    app.config['DEBUG'] = False

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/find-remedy", methods=["POST"])
def find_remedy():
    symptoms = request.form.get("symptoms", "")
    results = matcher.find_matching_remedies(symptoms)
    save_case({"symptoms": symptoms, "suggested_remedies": str([r.get("name") for r in results[:3]])})
    return render_template("results.html", symptoms=symptoms, remedies=results)

@app.route("/history")
def history():
    cases = load_all_cases(limit=20)
    return render_template("history.html", cases=cases)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/location")
def location():
    return render_template("location.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = get_user(email)
        if user and user["password"] == password:
            if user["role"] == "doctor":
                flash("Please use Doctor Login page", "warning")
                return redirect(url_for("doctor_login"))
            # Store full user data including id
            session["user"] = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user.get("phone"),
                "age": user.get("age"),
                "gender": user.get("gender"),
                "role": user["role"]
            }
            flash("Login successful!", "success")
            return redirect(url_for("patient_dashboard"))
        flash("Invalid email or password", "danger")
    return render_template("auth/login.html")

@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = get_user(email)
        if user and user["password"] == password and user["role"] == "doctor":
            # Store full user data including id
            session["user"] = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user.get("phone"),
                "role": user["role"]
            }
            flash("Welcome Doctor!", "success")
            return redirect(url_for("doctor_dashboard"))
        flash("Invalid credentials or not a doctor account", "danger")
    return render_template("auth/doctor_login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "password": request.form.get("password"),
            "phone": request.form.get("phone"),
            "age": request.form.get("age"),
            "gender": request.form.get("gender"),
            "role": "patient",
            "created_at": datetime.now().isoformat()
        }
        
        existing_user = get_user(user_data["email"])
        if existing_user:
            flash("Email already registered", "danger")
            return render_template("auth/register.html")
        
        if save_user(user_data):
            # Get the saved user to get the ID
            saved_user = get_user(user_data["email"])
            if saved_user:
                session["user"] = {
                    "id": saved_user["id"],
                    "name": saved_user["name"],
                    "email": saved_user["email"],
                    "phone": saved_user.get("phone"),
                    "age": saved_user.get("age"),
                    "gender": saved_user.get("gender"),
                    "role": "patient"
                }
            flash("Registration successful! You are now logged in.", "success")
            return redirect(url_for("patient_dashboard"))
        else:
            flash("Registration failed. Please try again.", "danger")
    
    return render_template("auth/register.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully", "info")
    return redirect(url_for("home"))

@app.route("/patient/dashboard")
def patient_dashboard():
    if "user" not in session or session["user"]["role"] != "patient":
        flash("Please login as patient", "warning")
        return redirect(url_for("login"))
    
    consultations = load_patient_consultations(session["user"]["email"])
    
    # Get appointments
    appointments = get_patient_appointments(session["user"]["id"])
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    upcoming = []
    past = []
    for a in appointments:
        appt_date = a['appointment_date']
        if isinstance(appt_date, str):
            appt_date_str = appt_date
        else:
            appt_date_str = appt_date.strftime('%Y-%m-%d') if hasattr(appt_date, 'strftime') else str(appt_date)
        
        if appt_date_str >= today_str and a['status'] == 'scheduled':
            upcoming.append(a)
        else:
            past.append(a)
    
    # Sort upcoming by date
    upcoming = sorted(upcoming, key=lambda x: (x['appointment_date'], x['appointment_time']))[:5]
    past = sorted(past, key=lambda x: (x['appointment_date'], x['appointment_time']), reverse=True)[:5]
    
    return render_template("patient/dashboard.html", 
                          consultations=consultations,
                          upcoming_appointments=upcoming,
                          past_appointments=past)

@app.route("/patient/consult", methods=["GET", "POST"])
def patient_consult():
    if "user" not in session or session["user"]["role"] != "patient":
        flash("Please login as patient", "warning")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        voice_filename = None
        if "voice_record" in request.files:
            voice_file = request.files["voice_record"]
            if voice_file.filename and allowed_file(voice_file.filename, ALLOWED_AUDIO):
                voice_filename = f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(voice_file.filename)}"
                voice_file.save(os.path.join(app.config["UPLOAD_FOLDER"], voice_filename))
        
        image_filenames = []
        if "images" in request.files:
            images = request.files.getlist("images")
            for img in images:
                if img.filename and allowed_file(img.filename, ALLOWED_IMAGES):
                    img_filename = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(img.filename)}"
                    img.save(os.path.join(app.config["UPLOAD_FOLDER"], img_filename))
                    image_filenames.append(img_filename)
        
        consultation = {
            "patient_email": session["user"]["email"],
            "patient_name": session["user"]["name"],
            "symptoms": request.form.get("symptoms"),
            "duration": request.form.get("duration"),
            "severity": request.form.get("severity"),
            "medical_history": request.form.get("medical_history"),
            "current_medications": request.form.get("current_medications"),
            "voice_record": voice_filename,
            "images": image_filenames,
            "status": "pending",
            "doctor_reply": None,
            "created_at": datetime.now().isoformat()
        }
        
        save_consultation(consultation)
        flash("Consultation submitted successfully!", "success")
        return redirect(url_for("patient_dashboard"))
    
    return render_template("patient/consult.html")

@app.route("/doctor/dashboard")
def doctor_dashboard():
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    consultations = load_consultations()
    pending_consultations = [c for c in consultations if c.get('status') == 'pending']
    replied_consultations = [c for c in consultations if c.get('status') == 'replied']
    pending_count = len(pending_consultations)
    replied_count = len(replied_consultations)
    
    # Get upcoming appointments for dashboard
    appointments = get_doctor_appointments(session["user"]["id"])
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    upcoming_appointments = []
    for a in appointments:
        appt_date = a['appointment_date']
        if isinstance(appt_date, str):
            appt_date_str = appt_date
        else:
            appt_date_str = appt_date.strftime('%Y-%m-%d') if hasattr(appt_date, 'strftime') else str(appt_date)
        
        if appt_date_str >= today_str and a['status'] == 'scheduled':
            upcoming_appointments.append(a)
    
    # Limit to next 5 upcoming appointments
    upcoming_appointments = sorted(upcoming_appointments, key=lambda x: (x['appointment_date'], x['appointment_time']))[:5]
    
    return render_template(
        "doctor/dashboard.html",
        consultations=consultations,
        pending_consultations=pending_consultations,
        replied_consultations=replied_consultations,
        pending_count=pending_count,
        replied_count=replied_count,
        upcoming_appointments=upcoming_appointments
    )

@app.route("/doctor/reply/<int:consultation_id>", methods=["GET", "POST"])
def doctor_reply(consultation_id):
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    consultations = load_consultations()
    consultation = next((c for c in consultations if c.get("id") == consultation_id), None)
    
    if not consultation:
        flash("Consultation not found", "danger")
        return redirect(url_for("doctor_dashboard"))
    
    patient_history = get_patient_history(consultation["patient_email"])
    patient_info = get_user(consultation["patient_email"])
    
    if request.method == "POST":
        reply = {
            "diagnosis": request.form.get("diagnosis"),
            "remedies": request.form.get("remedies"),
            "potency": request.form.get("potency"),
            "instructions": request.form.get("instructions"),
            "follow_up": request.form.get("follow_up"),
            "medicines_given": request.form.get("medicines_given"),
            "doctor_notes": request.form.get("doctor_notes"),
            "replied_at": datetime.now().isoformat()
        }
        update_consultation_reply(consultation_id, reply)
        flash("Reply sent to patient!", "success")
        return redirect(url_for("doctor_dashboard"))
    
    return render_template("doctor/reply.html",
                         consultation=consultation,
                         patient_history=patient_history,
                         patient_info=patient_info)

@app.route("/doctor/patient/<patient_email>")
def doctor_view_patient(patient_email):
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    patient_info = get_user(patient_email)
    patient_history = get_patient_history(patient_email)
    
    if not patient_info:
        flash("Patient not found", "danger")
        return redirect(url_for("doctor_dashboard"))
    
    return render_template("doctor/patient_detail.html",
                         patient=patient_info,
                         history=patient_history)

@app.route("/doctor/patient/<patient_email>/notes", methods=["POST"])
def save_patient_notes(patient_email):
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Unauthorized", "danger")
        return redirect(url_for("doctor_login"))
    
    notes = request.form.get("patient_notes", "")
    update_patient_notes(patient_email, notes)
    flash("Patient notes saved successfully!", "success")
    return redirect(url_for("doctor_view_patient", patient_email=patient_email))

@app.route("/doctor/delete-media/<int:consultation_id>/<media_type>", methods=["POST"])
def delete_media(consultation_id, media_type):
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Unauthorized", "danger")
        return redirect(url_for("doctor_login"))
    
    filename = request.form.get("filename")
    if filename:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    delete_consultation_media(consultation_id, media_type, filename)
    flash(f"{media_type.capitalize()} deleted", "success")
    return redirect(url_for("doctor_reply", consultation_id=consultation_id))

@app.route("/doctor/patients")
def doctor_patients():
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    patients = load_all_patients()
    all_consultations = load_consultations()
    for p in patients:
        p["consultation_count"] = len([c for c in all_consultations if c.get("patient_email") == p["email"]])
    return render_template("doctor/patients.html", patients=patients)

# ========== APPOINTMENT ROUTES ==========

@app.route("/patient/appointments")
def patient_appointments():
    if "user" not in session or session["user"]["role"] != "patient":
        flash("Please login as patient", "warning")
        return redirect(url_for("login"))
    
    patient_id = session["user"]["id"]
    appointments = get_patient_appointments(patient_id)
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    # Convert date strings to date objects for comparison
    upcoming = []
    past = []
    for a in appointments:
        # Handle both string and date object
        appt_date = a['appointment_date']
        if isinstance(appt_date, str):
            appt_date_str = appt_date
        else:
            appt_date_str = appt_date.strftime('%Y-%m-%d') if hasattr(appt_date, 'strftime') else str(appt_date)
        
        if appt_date_str >= today_str and a['status'] == 'scheduled':
            upcoming.append(a)
        else:
            past.append(a)
    
    return render_template("patient/appointments.html", upcoming=upcoming, past=past)

# Fixed time slots
MORNING_SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00"]
EVENING_SLOTS = ["18:00", "19:00", "20:00", "21:00", "22:00"]
ALL_SLOTS = MORNING_SLOTS + EVENING_SLOTS
MAX_PATIENTS_PER_SLOT = 15

def format_time_display(time_str):
    """Convert 24h to 12h format"""
    hour = int(time_str.split(':')[0])
    period = 'AM' if hour < 12 else 'PM'
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:00 {period}"

@app.route("/patient/book-appointment", methods=["GET", "POST"])
def book_appointment():
    if "user" not in session or session["user"]["role"] != "patient":
        flash("Please login as patient", "warning")
        return redirect(url_for("login"))
    
    doctors = get_all_doctors()
    
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        reason = request.form.get("reason")
        
        if not all([doctor_id, appointment_date, appointment_time]):
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("book_appointment"))
        
        # Check if slot has capacity
        booking_count = get_slot_booking_count(int(doctor_id), appointment_date, appointment_time)
        if booking_count >= MAX_PATIENTS_PER_SLOT:
            flash("This time slot is full. Please choose another slot.", "danger")
            return redirect(url_for("book_appointment"))
        
        appointment_data = {
            "patient_id": session["user"]["id"],
            "doctor_id": int(doctor_id),
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
            "reason": reason
        }
        
        appointment_id = save_appointment(appointment_data)
        if appointment_id:
            flash("🎉 Appointment booked successfully!", "success")
            return redirect(url_for("appointment_receipt", appointment_id=appointment_id))
        else:
            flash("Failed to book appointment. Please try again.", "danger")
    
    return render_template("patient/book_appointment.html", doctors=doctors)

@app.route("/patient/appointment-receipt/<int:appointment_id>")
def appointment_receipt(appointment_id):
    if "user" not in session:
        flash("Please login", "warning")
        return redirect(url_for("login"))
    
    appointment = get_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found", "danger")
        return redirect(url_for("patient_appointments"))
    
    # Check permission
    if appointment['patient_id'] != session["user"]["id"] and session["user"]["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("patient_appointments"))
    
    doctor = get_user_by_id(appointment['doctor_id'])
    patient = get_user_by_id(appointment['patient_id'])
    
    return render_template("patient/appointment_receipt.html", 
                          appointment=appointment, 
                          doctor=doctor, 
                          patient=patient)

@app.route("/patient/download-receipt/<int:appointment_id>")
def download_receipt(appointment_id):
    if "user" not in session:
        flash("Please login", "warning")
        return redirect(url_for("login"))
    
    appointment = get_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found", "danger")
        return redirect(url_for("patient_appointments"))
    
    # Check permission
    if appointment['patient_id'] != session["user"]["id"] and session["user"]["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("patient_appointments"))
    
    doctor = get_user_by_id(appointment['doctor_id'])
    patient = get_user_by_id(appointment['patient_id'])
    
    # Generate HTML for PDF
    html_content = render_template("patient/receipt_pdf.html", 
                                   appointment=appointment, 
                                   doctor=doctor, 
                                   patient=patient)
    
    # Return as HTML (for print/save as PDF)
    response = app.make_response(html_content)
    response.headers['Content-Type'] = 'text/html'
    return response

# Doctor appointment routes - fix date comparison
@app.route("/doctor/appointments")
def doctor_appointments():
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    appointments = get_doctor_appointments(session["user"]["id"])
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    upcoming = []
    past = []
    for a in appointments:
        appt_date = a['appointment_date']
        if isinstance(appt_date, str):
            appt_date_str = appt_date
        else:
            appt_date_str = appt_date.strftime('%Y-%m-%d') if hasattr(appt_date, 'strftime') else str(appt_date)
        
        if appt_date_str >= today_str and a['status'] == 'scheduled':
            upcoming.append(a)
        else:
            past.append(a)
    
    return render_template("doctor/appointments.html", upcoming=upcoming, past=past, today=today)

@app.route("/doctor/availability", methods=["GET", "POST"])
def doctor_availability():
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    if request.method == "POST":
        availability_date = request.form.get("availability_date")
        
        if not availability_date:
            flash("Please select a date", "danger")
            return redirect(url_for("doctor_availability"))
        
        # Get selected slots
        slots = {}
        for slot in ALL_SLOTS:
            slot_key = f"slot_{slot.replace(':', '')}"
            slots[slot] = 1 if request.form.get(slot_key) else 0
        
        # Check if any slot is selected
        if not any(slots.values()):
            # No slots selected - delete availability for this date (mark as off day)
            delete_doctor_availability(session["user"]["id"], availability_date)
            flash(f"Marked {availability_date} as OFF day", "info")
        else:
            save_doctor_availability(session["user"]["id"], availability_date, slots)
            flash(f"Availability saved for {availability_date}!", "success")
        
        return redirect(url_for("doctor_availability"))
    
    # Get all future availability
    availabilities = get_doctor_availability(session["user"]["id"])
    
    return render_template("doctor/availability.html", 
                          availabilities=availabilities,
                          all_slots=ALL_SLOTS,
                          morning_slots=MORNING_SLOTS,
                          evening_slots=EVENING_SLOTS)

@app.route("/api/doctor/availability/<date_str>")
def api_get_availability(date_str):
    if "user" not in session or session["user"]["role"] != "doctor":
        return jsonify({'error': 'Unauthorized'}), 401
    
    avail = get_availability_for_date(session["user"]["id"], date_str)
    if avail:
        slots = {
            '09:00': avail.get('slot_09', 0),
            '10:00': avail.get('slot_10', 0),
            '11:00': avail.get('slot_11', 0),
            '12:00': avail.get('slot_12', 0),
            '13:00': avail.get('slot_13', 0),
            '18:00': avail.get('slot_18', 0),
            '19:00': avail.get('slot_19', 0),
            '20:00': avail.get('slot_20', 0),
            '21:00': avail.get('slot_21', 0),
            '22:00': avail.get('slot_22', 0),
        }
        return jsonify({'exists': True, 'slots': slots})
    return jsonify({'exists': False, 'slots': {}})

@app.route("/api/available-slots/<int:doctor_id>/<date_str>")
def get_available_slots(doctor_id, date_str):
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format', 'slots': [], 'available': False})
    
    if selected_date < date.today():
        return jsonify({'slots': [], 'message': 'Cannot book for past dates', 'available': False})
    
    # Get doctor's availability for this date
    avail = get_availability_for_date(doctor_id, date_str)
    
    if not avail:
        # No availability set for this date - doctor not available
        return jsonify({
            'slots': [],
            'available': False,
            'message': 'Doctor is not available on this date. Please select another date.'
        })
    
    # Map slot columns to times
    slot_mapping = {
        '09:00': 'slot_09', '10:00': 'slot_10', '11:00': 'slot_11',
        '12:00': 'slot_12', '13:00': 'slot_13', '18:00': 'slot_18',
        '19:00': 'slot_19', '20:00': 'slot_20', '21:00': 'slot_21',
        '22:00': 'slot_22'
    }
    
    available_slots = []
    
    for slot_time, col_name in slot_mapping.items():
        # Check if slot is enabled by doctor
        if not avail.get(col_name, 0):
            continue
        
        # Skip past slots for today
        if selected_date == date.today():
            slot_hour = int(slot_time.split(':')[0])
            current_hour = datetime.now().hour
            if slot_hour <= current_hour:
                continue
        
        # Check booking count
        try:
            booking_count = get_slot_booking_count(doctor_id, date_str, slot_time)
        except:
            booking_count = 0
        
        if booking_count < MAX_PATIENTS_PER_SLOT:
            remaining = MAX_PATIENTS_PER_SLOT - booking_count
            available_slots.append({
                'time': slot_time,
                'remaining': remaining,
                'display': format_time_display(slot_time),
                'status': 'available' if remaining > 5 else 'filling'
            })
    
    if not available_slots:
        return jsonify({
            'slots': [],
            'available': True,
            'message': 'All slots are fully booked for this date.'
        })
    
    return jsonify({'slots': available_slots, 'available': True})

# ========== SERVE UPLOADS ==========
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/patient/cancel-appointment/<int:appointment_id>", methods=["POST"])
def cancel_appointment(appointment_id):
    if "user" not in session:
        flash("Please login", "warning")
        return redirect(url_for("login"))
    
    appointment = get_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found", "danger")
        return redirect(url_for("patient_appointments"))
    
    # Check permission
    if appointment['patient_id'] != session["user"]["id"] and session["user"]["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("patient_appointments"))
    
    cancellation_reason = request.form.get("cancellation_reason", "")
    update_appointment_status(appointment_id, 'cancelled', cancellation_reason)
    
    flash("Appointment cancelled successfully.", "success")
    
    if session["user"]["role"] == "doctor":
        return redirect(url_for("doctor_appointments"))
    return redirect(url_for("patient_appointments"))

@app.route("/patient/reschedule-appointment/<int:appointment_id>", methods=["GET", "POST"])
def reschedule_appointment_route(appointment_id):
    if "user" not in session:
        flash("Please login", "warning")
        return redirect(url_for("login"))
    
    appointment = get_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found", "danger")
        return redirect(url_for("patient_appointments"))
    
    if appointment['patient_id'] != session["user"]["id"] and session["user"]["role"] != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("patient_appointments"))
    
    doctor = get_user_by_id(appointment['doctor_id'])
    
    if request.method == "POST":
        new_date = request.form.get("appointment_date")
        new_time = request.form.get("appointment_time")
        
        # Check if new slot has capacity
        booking_count = get_slot_booking_count(appointment['doctor_id'], new_date, new_time)
        if booking_count >= MAX_PATIENTS_PER_SLOT:
            flash("This time slot is full. Please choose another slot.", "danger")
            return redirect(url_for("reschedule_appointment_route", appointment_id=appointment_id))
        
        reschedule_appointment(appointment_id, new_date, new_time)
        flash("Appointment rescheduled successfully!", "success")
        return redirect(url_for("patient_appointments"))
    
    return render_template("patient/reschedule_appointment.html", appointment=appointment, doctor=doctor)

@app.route("/doctor/complete-appointment/<int:appointment_id>", methods=["POST"])
def complete_appointment(appointment_id):
    if "user" not in session or session["user"]["role"] != "doctor":
        flash("Please login as doctor", "warning")
        return redirect(url_for("doctor_login"))
    
    appointment = get_appointment(appointment_id)
    if not appointment or appointment['doctor_id'] != session["user"]["id"]:
        flash("Appointment not found", "danger")
        return redirect(url_for("doctor_appointments"))
    
    notes = request.form.get("notes", "")
    update_appointment_status(appointment_id, 'completed')
    if notes:
        update_appointment_notes(appointment_id, notes)
    
    flash("Appointment marked as completed.", "success")
    return redirect(url_for("doctor_appointments"))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
