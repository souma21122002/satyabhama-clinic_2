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


def get_slot_bookings_for_range(doctor_id, start_date, end_date):
    """Return scheduled booking counts per slot within a range"""
    conn = get_db_connection()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT appointment_date, appointment_time, COUNT(*) as count
            FROM appointments
            WHERE doctor_id = ?
              AND appointment_date BETWEEN ? AND ?
              AND status = 'scheduled'
            GROUP BY appointment_date, appointment_time
            """,
            (doctor_id, start_date, end_date)
        )
        rows = cursor.fetchall()
        result = {}
        for row in rows:
            date_value = row['appointment_date']
            time_value = row['appointment_time']
            date_key = date_value if isinstance(date_value, str) else str(date_value)
            time_key = time_value if isinstance(time_value, str) else str(time_value)
            result.setdefault(date_key, {})[time_key] = row['count']
        return result
    except Exception as e:
        print(f"❌ Error loading slot counts: {e}")
        return {}
    finally:
        conn.close()

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
                documents TEXT,
                status TEXT DEFAULT 'pending',
                doctor_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_email) REFERENCES users(email)
            )
        """)

        # Ensure new columns exist for existing installs
        cur.execute("PRAGMA table_info(consultations)")
        existing_cons_columns = {row[1] for row in cur.fetchall()}
        if 'documents' not in existing_cons_columns:
            cur.execute("ALTER TABLE consultations ADD COLUMN documents TEXT")

        # Consultation media stored in Google Drive
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consultation_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultation_id INTEGER NOT NULL,
                patient_email TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                mime_type TEXT,
                media_type TEXT NOT NULL,
                size_bytes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE CASCADE,
                FOREIGN KEY (patient_email) REFERENCES users(email)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consultation_media_consultation_id ON consultation_media(consultation_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_consultation_media_patient_email ON consultation_media(patient_email)")
        
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
                is_off_day INTEGER DEFAULT 0,
                off_day_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES users(id),
                UNIQUE(doctor_id, availability_date)
            )
        """)

        # Ensure new columns exist for existing installs
        cur.execute("PRAGMA table_info(doctor_availability)")
        existing_columns = {row[1] for row in cur.fetchall()}
        if 'is_off_day' not in existing_columns:
            cur.execute("ALTER TABLE doctor_availability ADD COLUMN is_off_day INTEGER DEFAULT 0")
        if 'off_day_reason' not in existing_columns:
            cur.execute("ALTER TABLE doctor_availability ADD COLUMN off_day_reason TEXT")

        # Create site notices table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS site_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES users(id)
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
             current_medications, voice_record, images, documents, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(consultation.get('documents', [])),
            consultation.get('status', 'pending'),
            consultation.get('created_at', datetime.now())
        ))
        conn.commit()
        return int(cur.lastrowid)
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
        rows = cur.fetchall()
        consultation_ids = [int(r['id']) for r in rows]
        media_map = _load_media_map_for_consultations(conn, consultation_ids)
        consultations = []
        for row in rows:
            c = dict(row)
            c['images'] = json.loads(c['images']) if isinstance(c.get('images'), str) else []
            c['documents'] = json.loads(c['documents']) if isinstance(c.get('documents'), str) else []
            if c.get('doctor_reply'):
                c['doctor_reply'] = json.loads(c['doctor_reply']) if isinstance(c.get('doctor_reply'), str) else c['doctor_reply']
            c['drive_media'] = media_map.get(int(c['id']), [])
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
        cur.execute(
            "SELECT * FROM consultations WHERE patient_email = ? ORDER BY created_at DESC",
            (patient_email,),
        )
        rows = cur.fetchall()
        consultation_ids = [int(r['id']) for r in rows]
        media_map = _load_media_map_for_consultations(conn, consultation_ids)
        consultations = []
        for row in rows:
            c = dict(row)
            c['images'] = json.loads(c['images']) if isinstance(c.get('images'), str) else []
            c['documents'] = json.loads(c['documents']) if isinstance(c.get('documents'), str) else []
            if c.get('doctor_reply'):
                c['doctor_reply'] = json.loads(c['doctor_reply']) if isinstance(c.get('doctor_reply'), str) else c['doctor_reply']
            c['drive_media'] = media_map.get(int(c['id']), [])
            consultations.append(c)
        return consultations

    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        conn.close()


def get_consultation_by_id(consultation_id):
    """Get consultation by id"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM consultations WHERE id = ?", (consultation_id,))
        row = cur.fetchone()
        if not row:
            return None
        cons = dict(row)
        cons['images'] = json.loads(cons['images']) if isinstance(cons.get('images'), str) else []
        cons['documents'] = json.loads(cons['documents']) if isinstance(cons.get('documents'), str) else []
        if cons.get('doctor_reply'):
            cons['doctor_reply'] = json.loads(cons['doctor_reply']) if isinstance(cons.get('doctor_reply'), str) else cons['doctor_reply']
        cons['drive_media'] = list_consultation_media(consultation_id)
        return cons
    except Exception as e:
        print(f"❌ Error loading consultation: {e}")
        return None
    finally:
        conn.close()


def add_consultation_media(consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes=None):
    """Insert media row for a consultation"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO consultation_media
            (consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes, datetime.now()),
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception as e:
        print(f"❌ Error saving consultation media: {e}")
        return None
    finally:
        conn.close()


def list_consultation_media(consultation_id):
    """List media for a consultation"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes, created_at
            FROM consultation_media
            WHERE consultation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (consultation_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"❌ Error listing consultation media: {e}")
        return []
    finally:
        conn.close()


def get_consultation_media(media_id):
    """Get one media row"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes, created_at
            FROM consultation_media
            WHERE id = ?
            """,
            (media_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ Error loading consultation media: {e}")
        return None
    finally:
        conn.close()


def delete_consultation_media_row(media_id):
    """Delete media row (call Drive delete separately)"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM consultation_media WHERE id = ?", (media_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error deleting consultation media row: {e}")
        return False
    finally:
        conn.close()


def _load_media_map_for_consultations(conn, consultation_ids):
    if not consultation_ids:
        return {}
    placeholders = ",".join(["?"] * len(consultation_ids))
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes, created_at
            FROM consultation_media
            WHERE consultation_id IN ({placeholders})
            ORDER BY created_at ASC, id ASC
            """,
            tuple(consultation_ids),
        )
        rows = cur.fetchall()
        result = {}
        for r in rows:
            d = dict(r)
            cid = int(d['consultation_id'])
            result.setdefault(cid, []).append(d)
        return result
    except Exception as e:
        print(f"❌ Error loading media map: {e}")
        return {}
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
        elif media_type in ("document", "pdf"):
            cur.execute("SELECT documents FROM consultations WHERE id = ?", (consultation_id,))
            result = cur.fetchone()
            if result:
                docs = json.loads(result['documents']) if isinstance(result['documents'], str) else []
                if filename in docs:
                    docs.remove(filename)
                cur.execute("UPDATE consultations SET documents = ? WHERE id = ?", (json.dumps(docs), consultation_id))
        
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
            (doctor_id, availability_date, is_off_day, off_day_reason,
             slot_09, slot_10, slot_11, slot_12, slot_13,
             slot_18, slot_19, slot_20, slot_21, slot_22)
            VALUES (?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def set_doctor_off_day(doctor_id, availability_date, reason=None):
    """Mark a specific date as an off day"""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM doctor_availability WHERE doctor_id = ? AND availability_date = ?",
            (doctor_id, availability_date)
        )
        cursor.execute(
            """
            INSERT INTO doctor_availability
            (doctor_id, availability_date, is_off_day, off_day_reason,
             slot_09, slot_10, slot_11, slot_12, slot_13,
             slot_18, slot_19, slot_20, slot_21, slot_22)
            VALUES (?, ?, 1, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            """,
            (doctor_id, availability_date, reason)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error setting off day: {e}")
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


def get_doctor_availability_range(doctor_id, start_date, end_date):
    """Fetch availability records between two dates"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM doctor_availability
            WHERE doctor_id = ? AND availability_date BETWEEN ? AND ?
            ORDER BY availability_date
            """,
            (doctor_id, start_date, end_date)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Error loading availability range: {e}")
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

# ========== SITE NOTICE FUNCTIONS ==========

def save_site_notice(title, message, doctor_id=None, is_active=True):
    """Create a new site notice"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO site_notices (doctor_id, title, message, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doctor_id, title, message, 1 if is_active else 0, datetime.now(), datetime.now())
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error saving site notice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def list_site_notices(active_only=False):
    """Fetch site notices"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        query = """
            SELECT id, doctor_id, title, message, is_active, created_at, updated_at
            FROM site_notices
        """
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY updated_at DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        notices = []
        for row in rows:
            item = dict(row)
            for ts_field in ("created_at", "updated_at"):
                value = item.get(ts_field)
                if isinstance(value, datetime):
                    item[ts_field] = value.isoformat()
            item['is_active'] = bool(item.get('is_active'))
            notices.append(item)
        return notices
    except Exception as e:
        print(f"❌ Error fetching site notices: {e}")
        return []
    finally:
        conn.close()


def get_active_site_notice():
    notices = list_site_notices(active_only=True)
    return notices[0] if notices else None


def set_site_notice_active(notice_id, is_active):
    """Toggle notice visibility"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE site_notices
            SET is_active = ?, updated_at = ?
            WHERE id = ?
            """,
            (1 if is_active else 0, datetime.now(), notice_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Error updating site notice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_site_notice(notice_id):
    """Delete a site notice"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM site_notices WHERE id = ?", (notice_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Error deleting site notice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def clear_site_notice():
    """Deactivate active notices"""
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE site_notices
            SET is_active = 0, updated_at = ?
            WHERE is_active = 1
            """,
            (datetime.now(),)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error clearing site notice: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
