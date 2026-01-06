import json
import os
import sqlite3
from datetime import datetime, date

DB_FILE = "homeopathy.db"

def get_db_connection():
    """Get SQLite connection"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize SQLite database"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT,
                age INTEGER,
                gender TEXT,
                role TEXT DEFAULT 'patient',
                doctor_notes TEXT,
                notes_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create consultations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_email TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                duration TEXT,
                severity TEXT,
                medical_history TEXT,
                current_medications TEXT,
                voice_record TEXT,
                images TEXT,
                status TEXT DEFAULT 'pending',
                doctor_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_email) REFERENCES users(email)
            )
        """)
        
        # Create case history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS case_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symptoms TEXT NOT NULL,
                suggested_remedies TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create appointments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                duration INTEGER DEFAULT 30,
                status TEXT DEFAULT 'scheduled',
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TIMESTAMP,
                cancellation_reason TEXT,
                FOREIGN KEY (patient_id) REFERENCES users(id),
                FOREIGN KEY (doctor_id) REFERENCES users(id)
            )
        """)
        
        # Create doctor availability table - DATE WISE
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doctor_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                availability_date DATE NOT NULL,
                slot_09 INTEGER DEFAULT 0,
                slot_10 INTEGER DEFAULT 0,
                slot_11 INTEGER DEFAULT 0,
                slot_12 INTEGER DEFAULT 0,
                slot_13 INTEGER DEFAULT 0,
                slot_18 INTEGER DEFAULT 0,
                slot_19 INTEGER DEFAULT 0,
                slot_20 INTEGER DEFAULT 0,
                slot_21 INTEGER DEFAULT 0,
                slot_22 INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES users(id),
                UNIQUE(doctor_id, availability_date)
            )
        """)
        
        conn.commit()
        print("✅ Database initialized")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def save_user(user_data):
    """Save user"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (name, email, password, phone, age, gender, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_data['name'],
            user_data['email'],
            user_data['password'],
            user_data.get('phone'),
            user_data.get('age'),
            user_data.get('gender'),
            user_data.get('role', 'patient'),
            user_data.get('created_at', datetime.now())
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def get_user(email):
    """Get user by email"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        conn.close()

def load_all_patients():
    """Get all patients"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE role = 'patient' ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()

def save_consultation(consultation):
    """Save consultation"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO consultations 
            (patient_email, patient_name, symptoms, duration, severity, medical_history, 
             current_medications, voice_record, images, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            consultation['patient_email'],
            consultation['patient_name'],
            consultation['symptoms'],
            consultation.get('duration'),
            consultation.get('severity'),
            consultation.get('medical_history'),
            consultation.get('current_medications'),
            consultation.get('voice_record'),
            json.dumps(consultation.get('images', [])),
            consultation.get('status', 'pending'),
            consultation.get('created_at', datetime.now())
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def load_consultations():
    """Get all consultations"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM consultations ORDER BY created_at DESC")
        consultations = []
            rows = cur.fetchall()
            for row in rows:
            c = dict(row)
            c['images'] = json.loads(c['images']) if isinstance(c['images'], str) else []
            consultations.append(c)
        return consultations
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()

def load_patient_consultations(patient_email):
    """Get patient consultations"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM consultations WHERE patient_email = ? ORDER BY created_at DESC", (patient_email,))
        consultations = []
            rows = cur.fetchall()
            for row in rows:
            c = dict(row)
            c['images'] = json.loads(c['images']) if isinstance(c['images'], str) else []
            consultations.append(c)
        return consultations
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()

def get_patient_history(patient_email):
    """Get patient history"""
    return load_patient_consultations(patient_email)

def update_consultation_reply(consultation_id, reply):
    """Update reply"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE consultations SET doctor_reply = ?, status = 'replied' WHERE id = ?
        """, (json.dumps(reply), consultation_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def update_patient_notes(patient_email, notes):
    """Update notes"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET doctor_notes = ?, notes_updated = ? WHERE email = ?
        """, (notes, datetime.now(), patient_email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def delete_consultation_media(consultation_id, media_type, filename):
    """Delete media"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        if media_type == "audio":
            cur.execute("UPDATE consultations SET voice_record = NULL WHERE id = ?", (consultation_id,))
        elif media_type == "image":
            cur.execute("SELECT images FROM consultations WHERE id = ?", (consultation_id,))
            result = cur.fetchone()
            if result:
                images = json.loads(result['images']) if isinstance(result['images'], str) else []
                if filename in images:
                    images.remove(filename)
                cur.execute("UPDATE consultations SET images = ? WHERE id = ?", (json.dumps(images), consultation_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def save_case(case_data):
    """Save case"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO case_history (symptoms, suggested_remedies, created_at)
            VALUES (?, ?, ?)
        """, (case_data.get('symptoms'), case_data.get('suggested_remedies'), datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()

def load_all_cases(limit=20):
    """Get cases"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM case_history ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()

# ========== APPOINTMENT FUNCTIONS ==========

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
            return dict(row) if row else None
        return None
    except Exception as e:
        print(f"❌ Error getting user by id: {e}")
        return None
    finally:
        conn.close()

def get_all_doctors():
    """Get all doctors"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE role = 'doctor' ORDER BY name")
        rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading doctors: {e}")
        return []
    finally:
        conn.close()

def save_doctor_availability(doctor_id, availability_date, slots):
    """Save doctor availability for a specific date"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        # Delete existing availability for this date
        cursor.execute("DELETE FROM doctor_availability WHERE doctor_id = ? AND availability_date = ?", 
                      (doctor_id, availability_date))
        
        print(f"🔧 Saving availability for doctor {doctor_id} on {availability_date}")
        print(f"   Slots: {slots}")
        
        # Insert new availability
            cursor.execute("""
                INSERT INTO doctor_availability 
                (doctor_id, availability_date, slot_09, slot_10, slot_11, slot_12, slot_13, 
                 slot_18, slot_19, slot_20, slot_21, slot_22)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doctor_id, availability_date,
                int(bool(slots.get('09:00', 0))), int(bool(slots.get('10:00', 0))), int(bool(slots.get('11:00', 0))),
                int(bool(slots.get('12:00', 0))), int(bool(slots.get('13:00', 0))), int(bool(slots.get('18:00', 0))),
                int(bool(slots.get('19:00', 0))), int(bool(slots.get('20:00', 0))), int(bool(slots.get('21:00', 0))),
                int(bool(slots.get('22:00', 0)))
            ))
        conn.commit()
        print(f"✅ Availability saved successfully!")
        return True
    except Exception as e:
        print(f"❌ Error saving availability: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def get_doctor_availability(doctor_id):
    """Get all doctor's availability"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        # Get ALL records first without any filtering
        cursor.execute("""
            SELECT * FROM doctor_availability 
            WHERE doctor_id = ?
            ORDER BY availability_date
        """, (doctor_id,))
        rows = cursor.fetchall()
        
        result = [dict(row) for row in rows]
        print(f"🔍 BEFORE filter - Total records in DB: {len(result)}")
        
        if result:
            print(f"   Sample date from DB: '{result[0]['availability_date']}' (type: {type(result[0]['availability_date'])})")
        
        # Filter for today and future dates
        today = date.today()
        print(f"   Today's date: '{today}' (type: {type(today)})")
        
        # Convert both to strings for comparison
        today_str = today.strftime('%Y-%m-%d')
        filtered = []
        for r in result:
            avail_date = r['availability_date']
            # Handle if it's already a date object
            if isinstance(avail_date, date):
                avail_date_str = avail_date.strftime('%Y-%m-%d')
            else:
                avail_date_str = str(avail_date)
            
            print(f"   Comparing: '{avail_date_str}' >= '{today_str}' = {avail_date_str >= today_str}")
            
            if avail_date_str >= today_str:
                filtered.append(r)
        
        print(f"   AFTER filter: {len(filtered)} dates")
        return filtered
        
    except Exception as e:
        print(f"❌ Error loading availability: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

def get_availability_for_date(doctor_id, availability_date):
    """Get doctor's availability for a specific date"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM doctor_availability 
            WHERE doctor_id = ? AND availability_date = ?
        """, (doctor_id, availability_date))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ Error loading date availability: {e}")
        return None
    finally:
        conn.close()

def get_availability_for_day(doctor_id, day_of_week):
    """Deprecated - kept for compatibility"""
    return None

def delete_doctor_availability(doctor_id, availability_date):
    """Delete availability for a specific date"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM doctor_availability WHERE doctor_id = ? AND availability_date = ?", 
                      (doctor_id, availability_date))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error deleting availability: {e}")
        return False
    finally:
        conn.close()

def save_appointment(appointment_data):
    """Save appointment"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, duration, status, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            appointment_data['patient_id'], appointment_data['doctor_id'],
            appointment_data['appointment_date'], appointment_data['appointment_time'],
            appointment_data.get('duration', 30), appointment_data.get('status', 'scheduled'),
            appointment_data.get('reason'), datetime.now().isoformat()
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"❌ Error saving appointment: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_appointment(appointment_id):
    """Get appointment by ID"""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"❌ Error getting appointment: {e}")
        return None
    finally:
        conn.close()

def get_appointments_for_slot(doctor_id, appointment_date, appointment_time):
    """Get count of appointments for a slot"""
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        # Handle time format - might be "09:00" or "09:00:00"
        time_patterns = [appointment_time, f"{appointment_time}:00"]
        
        cursor.execute("""
            SELECT COUNT(*) FROM appointments 
            WHERE doctor_id = ? AND appointment_date = ? 
            AND (appointment_time = ? OR appointment_time = ?)
            AND status = 'scheduled'
        """, (doctor_id, appointment_date, time_patterns[0], time_patterns[1]))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        print(f"❌ Error checking slot: {e}")
        return 0
    finally:
        conn.close()

def get_slot_booking_count(doctor_id, appointment_date, appointment_time):
    """Get number of bookings for a specific slot"""
    return get_appointments_for_slot(doctor_id, appointment_date, appointment_time)

def get_patient_appointments(patient_id):
    """Get all appointments for a patient"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, u.name as doctor_name, u.email as doctor_email
            FROM appointments a
            JOIN users u ON a.doctor_id = u.id
            WHERE a.patient_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """, (patient_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading patient appointments: {e}")
        return []
    finally:
        conn.close()

def get_doctor_appointments(doctor_id):
    """Get all appointments for a doctor"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, u.name as patient_name, u.email as patient_email, u.phone as patient_phone
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            WHERE a.doctor_id = ?
            ORDER BY a.appointment_date, a.appointment_time
        """, (doctor_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading doctor appointments: {e}")
        return []
    finally:
        conn.close()

def update_appointment_status(appointment_id, status, cancellation_reason=None):
    """Update appointment status"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        if status == 'cancelled':
            cursor.execute("""
                UPDATE appointments SET status = ?, cancelled_at = ?, cancellation_reason = ?, updated_at = ? WHERE id = ?
            """, (status, datetime.now().isoformat(), cancellation_reason, datetime.now().isoformat(), appointment_id))
        else:
            cursor.execute("UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?", (status, datetime.now().isoformat(), appointment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating appointment: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def reschedule_appointment(appointment_id, new_date, new_time):
    """Reschedule appointment"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE appointments SET appointment_date = ?, appointment_time = ?, status = 'scheduled', updated_at = ? WHERE id = ?
        """, (new_date, new_time, datetime.now().isoformat(), appointment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error rescheduling: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_appointment_notes(appointment_id, notes):
    """Update appointment notes"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET notes = ?, updated_at = ? WHERE id = ?", (notes, datetime.now().isoformat(), appointment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating notes: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
