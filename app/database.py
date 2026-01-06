import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

def get_db_connection():
    """Get PostgreSQL connection for production"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise Exception("DATABASE_URL not set")
        
        # Render uses postgres:// but psycopg2 needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def init_db():
    """Initialize PostgreSQL database"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                age INTEGER,
                gender VARCHAR(20),
                role VARCHAR(20) DEFAULT 'patient',
                doctor_notes TEXT,
                notes_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create consultations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consultations (
                id SERIAL PRIMARY KEY,
                patient_email VARCHAR(255) NOT NULL,
                patient_name VARCHAR(255) NOT NULL,
                symptoms TEXT NOT NULL,
                duration VARCHAR(100),
                severity VARCHAR(50),
                medical_history TEXT,
                current_medications TEXT,
                voice_record VARCHAR(255),
                images TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                doctor_reply JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_email) REFERENCES users(email)
            )
        """)
        
        # Create case history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS case_history (
                id SERIAL PRIMARY KEY,
                symptoms TEXT NOT NULL,
                suggested_remedies TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create appointments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id SERIAL PRIMARY KEY,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                duration INTEGER DEFAULT 30,
                status VARCHAR(20) DEFAULT 'scheduled',
                reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TIMESTAMP,
                cancellation_reason TEXT,
                FOREIGN KEY (patient_id) REFERENCES users(id),
                FOREIGN KEY (doctor_id) REFERENCES users(id)
            )
        """)
        
        # Create doctor availability table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doctor_availability (
                id SERIAL PRIMARY KEY,
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
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
        print(f"Error saving user: {e}")
        conn.rollback()
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
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None
    finally:
        conn.close()

def load_all_patients():
    """Get all patients"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE role = 'patient' ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading patients: {e}")
        return []
    finally:
        conn.close()

def save_consultation(consultation):
    """Save consultation"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO consultations 
                (patient_email, patient_name, symptoms, duration, severity, medical_history, 
                 current_medications, voice_record, images, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        print(f"❌ Error saving consultation: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def load_consultations():
    """Get all consultations"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM consultations ORDER BY created_at DESC")
            rows = cur.fetchall()
            consultations = []
            for row in rows:
                cons = dict(row)
                if cons.get('images'):
                    cons['images'] = json.loads(cons['images']) if isinstance(cons['images'], str) else cons['images']
                else:
                    cons['images'] = []
                if cons.get('doctor_reply'):
                    cons['doctor_reply'] = json.loads(cons['doctor_reply']) if isinstance(cons['doctor_reply'], str) else cons['doctor_reply']
                consultations.append(cons)
            return consultations
    except Exception as e:
        print(f"❌ Error loading consultations: {e}")
        return []
    finally:
        conn.close()

def load_patient_consultations(patient_email):
    """Get patient consultations"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM consultations WHERE patient_email = %s ORDER BY created_at DESC", (patient_email,))
            rows = cur.fetchall()
            consultations = []
            for row in rows:
                cons = dict(row)
                if cons.get('images'):
                    cons['images'] = json.loads(cons['images']) if isinstance(cons['images'], str) else cons['images']
                else:
                    cons['images'] = []
                if cons.get('doctor_reply'):
                    cons['doctor_reply'] = json.loads(cons['doctor_reply']) if isinstance(cons['doctor_reply'], str) else cons['doctor_reply']
                consultations.append(cons)
            return consultations
    except Exception as e:
        print(f"❌ Error loading patient consultations: {e}")
        return []
    finally:
        conn.close()

def get_patient_history(patient_email):
    """Get patient history"""
    return load_patient_consultations(patient_email)

def update_consultation_reply(consultation_id, reply):
    """Update consultation reply"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE consultations 
                SET doctor_reply = %s::jsonb, status = 'replied'
                WHERE id = %s
            """, (json.dumps(reply), consultation_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error updating reply: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_patient_notes(patient_email, notes):
    """Update patient notes"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET doctor_notes = %s, notes_updated = %s
                WHERE email = %s
            """, (notes, datetime.now(), patient_email))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error updating notes: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_consultation_media(consultation_id, media_type, filename):
    """Delete media"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            if media_type == "audio":
                cur.execute("UPDATE consultations SET voice_record = NULL WHERE id = %s", (consultation_id,))
            elif media_type == "image":
                cur.execute("SELECT images FROM consultations WHERE id = %s", (consultation_id,))
                result = cur.fetchone()
                if result:
                    images = json.loads(result[0]) if isinstance(result[0], str) else []
                    if filename in images:
                        images.remove(filename)
                    cur.execute("UPDATE consultations SET images = %s WHERE id = %s", (json.dumps(images), consultation_id))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error deleting media: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def save_case(case_data):
    """Save case"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO case_history (symptoms, suggested_remedies, created_at)
                VALUES (%s, %s, %s)
            """, (case_data.get('symptoms'), case_data.get('suggested_remedies'), datetime.now()))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error saving case: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def load_all_cases(limit=20):
    """Get all cases"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, symptoms, suggested_remedies, created_at 
                FROM case_history ORDER BY created_at DESC LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            cases = []
            for row in rows:
                case = {
                    'id': row[0],
                    'symptoms': row[1],
                    'suggested_remedies': row[2],
                    'created_at': row[3]
                }
                cases.append(case)
            return cases
    except Exception as e:
        print(f"❌ Error loading cases: {e}")
        return []
    finally:
        if conn:
            conn.close()

# ========== APPOINTMENT FUNCTIONS ==========

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
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
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE role = 'doctor' ORDER BY name")
            rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("DELETE FROM doctor_availability WHERE doctor_id = %s AND availability_date = %s", 
                       (doctor_id, availability_date))
            
            cur.execute("""
                INSERT INTO doctor_availability 
                (doctor_id, availability_date, slot_09, slot_10, slot_11, slot_12, slot_13, 
                 slot_18, slot_19, slot_20, slot_21, slot_22)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                doctor_id, availability_date,
                int(bool(slots.get('09:00', False))), int(bool(slots.get('10:00', False))), int(bool(slots.get('11:00', False))),
                int(bool(slots.get('12:00', False))), int(bool(slots.get('13:00', False))), int(bool(slots.get('18:00', False))),
                int(bool(slots.get('19:00', False))), int(bool(slots.get('20:00', False))), int(bool(slots.get('21:00', False))),
                int(bool(slots.get('22:00', False)))
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error saving availability: {e}")
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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM doctor_availability 
                WHERE doctor_id = %s AND availability_date >= CURRENT_DATE
                ORDER BY availability_date
            """, (doctor_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading availability: {e}")
        return []
    finally:
        conn.close()

def get_availability_for_date(doctor_id, availability_date):
    """Get doctor's availability for a specific date"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM doctor_availability 
                WHERE doctor_id = %s AND availability_date = %s
            """, (doctor_id, availability_date))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
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
        with conn.cursor() as cur:
            cur.execute("DELETE FROM doctor_availability WHERE doctor_id = %s AND availability_date = %s", 
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO appointments 
                (patient_id, doctor_id, appointment_date, appointment_time, duration, status, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                appointment_data['patient_id'],
                appointment_data['doctor_id'],
                appointment_data['appointment_date'],
                appointment_data['appointment_time'],
                appointment_data.get('duration', 30),
                appointment_data.get('status', 'scheduled'),
                appointment_data.get('reason'),
                datetime.now()
            ))
            appointment_id = cur.fetchone()[0]
            conn.commit()
            return appointment_id
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
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
            row = cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM appointments 
                WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s AND status = 'scheduled'
            """, (doctor_id, appointment_date, appointment_time))
            count = cur.fetchone()[0]
            return count
    except Exception as e:
        print(f"❌ Error checking slot: {e}")
        return 0
    finally:
        conn.close()

def get_slot_booking_count(doctor_id, appointment_date, appointment_time):
    """Get number of bookings for a specific slot"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM appointments 
                WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s AND status = 'scheduled'
            """, (doctor_id, appointment_date, appointment_time))
            return cur.fetchone()[0]
    except Exception as e:
        print(f"❌ Error getting slot count: {e}")
        return 0
    finally:
        conn.close()

def get_patient_appointments(patient_id):
    """Get all appointments for a patient"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.*, u.name as doctor_name, u.email as doctor_email
                FROM appointments a
                JOIN users u ON a.doctor_id = u.id
                WHERE a.patient_id = %s
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
            """, (patient_id,))
            rows = cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.*, u.name as patient_name, u.email as patient_email, u.phone as patient_phone
                FROM appointments a
                JOIN users u ON a.patient_id = u.id
                WHERE a.doctor_id = %s
                ORDER BY a.appointment_date, a.appointment_time
            """, (doctor_id,))
            rows = cur.fetchall()
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
        with conn.cursor() as cur:
            if status == 'cancelled':
                cur.execute("""
                    UPDATE appointments 
                    SET status = %s, cancelled_at = %s, cancellation_reason = %s, updated_at = %s
                    WHERE id = %s
                """, (status, datetime.now(), cancellation_reason, datetime.now(), appointment_id))
            else:
                cur.execute("""
                    UPDATE appointments 
                    SET status = %s, updated_at = %s
                    WHERE id = %s
                """, (status, datetime.now(), appointment_id))
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
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE appointments 
                SET appointment_date = %s, appointment_time = %s, status = 'scheduled', updated_at = %s
                WHERE id = %s
            """, (new_date, new_time, datetime.now(), appointment_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error rescheduling appointment: {e}")
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
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE appointments 
                SET notes = %s, updated_at = %s
                WHERE id = %s
            """, (notes, datetime.now(), appointment_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error updating notes: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
