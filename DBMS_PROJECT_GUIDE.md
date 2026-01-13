# Homeopathy Project — Complete DBMS Guide for Interviews

This document explains **how the database works**, **table relationships**, **data flow for every action**, and **security/privacy** aspects. Use this to confidently answer DBMS interview questions.

---

## 1. Database Architecture

### 1.1 Dual Database Support
```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
├─────────────────────────────────────────────────────────────┤
│  if FLASK_ENV == "production":                              │
│      use app/database.py      → PostgreSQL (cloud)          │
│  else:                                                       │
│      use app/database_local.py → SQLite (local file)        │
└─────────────────────────────────────────────────────────────┘
```

**Why two databases?**
| Aspect | SQLite (Development) | PostgreSQL (Production) |
|--------|---------------------|------------------------|
| Setup | Zero config, single file | Requires server/cloud |
| Concurrency | Limited (file locks) | Excellent (MVCC) |
| JSON support | TEXT only | Native JSONB |
| Best for | Local testing | Real users |

### 1.2 Connection Handling
```python
# PostgreSQL (production)
def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    return conn

# SQLite (development)
def get_db_connection():
    conn = sqlite3.connect("homeopathy.db")
    conn.row_factory = sqlite3.Row  # Returns dict-like rows
    return conn
```

**Interview Q: Why `RealDictCursor` / `Row`?**
> These return rows as dictionaries instead of tuples, so we can access `row['email']` instead of `row[2]`. Makes code readable and position-independent.

---

## 2. Entity-Relationship Diagram (ERD)

```
┌─────────────────┐
│     users       │
│─────────────────│
│ id (PK)         │◄──────────────────────────────────────────────┐
│ email (UNIQUE)  │◄─────────────────────┐                        │
│ name            │                      │                        │
│ password        │                      │                        │
│ phone           │                      │                        │
│ role            │                      │                        │
│ doctor_notes    │                      │                        │
└────────┬────────┘                      │                        │
         │                               │                        │
         │ 1:N                           │                        │
         ▼                               │                        │
┌─────────────────┐              ┌───────┴───────┐        ┌───────┴───────┐
│ consultations   │              │ consultation  │        │ appointments  │
│─────────────────│              │    _media     │        │───────────────│
│ id (PK)         │◄─────────────│───────────────│        │ id (PK)       │
│ patient_email   │──────────────│ consultation  │        │ patient_id ───┤► users.id
│   (FK→email)    │              │   _id (FK)    │        │ doctor_id ────┤► users.id
│ symptoms        │              │ patient_email │        │ date, time    │
│ status          │              │ drive_file_id │        │ status        │
│ doctor_reply    │              └───────────────┘        └───────────────┘
└─────────────────┘
         │
         │ Referenced by
         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  case_history   │       │ doctor_         │       │  site_notices   │
│─────────────────│       │   availability  │       │─────────────────│
│ id (PK)         │       │─────────────────│       │ id (PK)         │
│ symptoms        │       │ doctor_id (FK)  │       │ doctor_id (FK)  │
│ suggested_      │       │ date            │       │ title, message  │
│   remedies      │       │ slot_09..22     │       │ is_active       │
└─────────────────┘       │ is_off_day      │       └─────────────────┘
                          └─────────────────┘
```

### 2.1 Relationship Types

| Relationship | Type | Explanation |
|-------------|------|-------------|
| users → consultations | 1:N | One patient can have many consultations |
| users → appointments | 1:N | One patient/doctor can have many appointments |
| consultations → consultation_media | 1:N | One consultation can have many files |
| users → doctor_availability | 1:N | One doctor sets availability for many dates |
| users → site_notices | 1:N | One doctor can post many notices |

---

## 3. How Each Database Action Works

### 3.1 User Registration Flow

```
User fills form → POST /register → save_user() → INSERT into users → Auto-login
```

**Database Operation:**
```sql
INSERT INTO users (name, email, password, phone, age, gender, role, created_at)
VALUES ('John Doe', 'john@email.com', 'mypassword123', '+91...', 30, 'male', 'patient', NOW())
```

**Code Flow:**
```python
def save_user(user_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (name, email, password, phone, age, gender, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_data['name'], user_data['email'], user_data['password'], ...))
    conn.commit()  # ← Transaction committed here
    conn.close()
```

**Interview Q: What happens if email already exists?**
> The `email UNIQUE` constraint causes an **IntegrityError**. The code catches this and shows "Email already registered" message.

---

### 3.2 User Login & Authentication Flow

```
POST /login → get_user(email) → SELECT from users → Compare password → Create session
```

**Database Operation:**
```sql
SELECT * FROM users WHERE email = 'john@email.com'
```

**Code Flow:**
```python
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    
    user = get_user(email)  # ← Database SELECT
    
    if user and user["password"] == password:  # ← Plain comparison (INSECURE!)
        session["user"] = {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
        # Session stored in encrypted cookie
```

**Interview Q: How is the user session maintained?**
> Flask uses a **signed cookie** with `app.secret_key`. The session data is serialized, signed (HMAC), and stored client-side. Server verifies signature on each request.

---

### 3.3 Patient Submits Consultation

```
POST /patient/consult → save_consultation() → INSERT → Upload files to Drive → Link media
```

**Step 1: Insert consultation record**
```sql
INSERT INTO consultations 
(patient_email, patient_name, symptoms, duration, severity, 
 medical_history, current_medications, status, created_at)
VALUES ('john@email.com', 'John Doe', 'headache, fever', '3 days', 
        'moderate', 'none', 'paracetamol', 'pending', NOW())
RETURNING id  -- Returns the new consultation ID
```

**Step 2: Upload files to Google Drive**
```python
uploaded = DRIVE_STORAGE.upload_file(
    folder_id=consultation_folder_id,
    filename="img_20260113_report.jpg",
    fileobj=image_file.stream
)
```

**Step 3: Link media to consultation**
```sql
INSERT INTO consultation_media 
(consultation_id, patient_email, drive_file_id, file_name, mime_type, media_type, size_bytes)
VALUES (42, 'john@email.com', 'DRIVE_FILE_ID_ABC123', 'img_report.jpg', 'image/jpeg', 'image', 102400)
```

**Interview Q: Why store `patient_email` in both `consultations` and `consultation_media`?**
> **Denormalization for performance.** Avoids JOIN when checking media ownership. Trade-off: data duplication vs query speed.

---

### 3.4 Doctor Views & Replies to Consultation

```
GET /doctor/reply/42 → load_consultations() → SELECT with media → Display
POST /doctor/reply/42 → update_consultation_reply() → UPDATE → Set status='replied'
```

**Loading consultation with related data:**
```python
# Main query
SELECT * FROM consultations WHERE id = 42

# Load attached media (separate query)
SELECT * FROM consultation_media WHERE consultation_id = 42

# Load patient history (all their consultations)
SELECT * FROM consultations WHERE patient_email = 'john@email.com' ORDER BY created_at DESC
```

**Saving doctor's reply:**
```sql
UPDATE consultations 
SET doctor_reply = '{"diagnosis": "Viral fever", "remedies": "Belladonna 30C", ...}',
    status = 'replied'
WHERE id = 42
```

**Interview Q: Why is `doctor_reply` stored as JSON instead of separate columns?**
> **Flexibility.** The reply structure can vary (different fields for different cases). JSONB in Postgres allows querying inside JSON. Trade-off: harder to enforce schema, but easier to evolve.

---

### 3.5 Booking an Appointment

```
GET /patient/book-appointment → Show doctors → Select date → API: get slots → Select slot → POST → save_appointment()
```

**Step 1: Get available doctors**
```sql
SELECT * FROM users WHERE role = 'doctor' ORDER BY name
```

**Step 2: Check doctor's availability for selected date**
```sql
SELECT * FROM doctor_availability 
WHERE doctor_id = 1 AND availability_date = '2026-01-15'
```
Returns which slots (slot_09, slot_10, etc.) are enabled.

**Step 3: Check current bookings for capacity**
```sql
SELECT COUNT(*) FROM appointments 
WHERE doctor_id = 1 
  AND appointment_date = '2026-01-15' 
  AND appointment_time = '10:00'
  AND status = 'scheduled'
```
If count < MAX_PATIENTS_PER_SLOT (15), slot is available.

**Step 4: Create appointment**
```sql
INSERT INTO appointments 
(patient_id, doctor_id, appointment_date, appointment_time, duration, status, reason, created_at)
VALUES (5, 1, '2026-01-15', '10:00', 30, 'scheduled', 'Follow-up checkup', NOW())
RETURNING id
```

**Interview Q: How do you prevent overbooking under concurrent requests?**
> Current code uses **read-then-write** which has a **race condition**. Better approach:
> 1. Use **database transactions** with `SELECT ... FOR UPDATE` (row-level lock)
> 2. Or use an **atomic counter** column in `doctor_availability`
> 3. Or add a **UNIQUE constraint** on `(doctor_id, date, time, patient_id)` to prevent duplicates

---

### 3.6 Doctor Sets Availability

```
POST /doctor/availability → save_doctor_availability() → DELETE old + INSERT new (UPSERT pattern)
```

**Database Operation (UPSERT pattern):**
```python
# Step 1: Remove existing record for this date
DELETE FROM doctor_availability WHERE doctor_id = 1 AND availability_date = '2026-01-20'

# Step 2: Insert new record
INSERT INTO doctor_availability 
(doctor_id, availability_date, slot_09, slot_10, slot_11, slot_12, slot_13, 
 slot_18, slot_19, slot_20, slot_21, slot_22, is_off_day)
VALUES (1, '2026-01-20', 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, FALSE)
```

**Interview Q: Why DELETE + INSERT instead of UPDATE?**
> Simpler logic when record may or may not exist. Alternative: Use `INSERT ... ON CONFLICT UPDATE` (Postgres) or check existence first.

**Interview Q: Why use columns `slot_09`, `slot_10` instead of normalized rows?**
> **Denormalized for simplicity.** Each date = one row. Trade-off: 
> - ✅ Simple queries, atomic updates
> - ❌ Inflexible (can't add new time slots without schema change)
> 
> Normalized alternative: `doctor_slots(doctor_id, date, time, enabled)`

---

### 3.7 Cancelling / Rescheduling Appointment

**Cancel:**
```sql
UPDATE appointments 
SET status = 'cancelled', 
    cancelled_at = NOW(), 
    cancellation_reason = 'Patient requested'
WHERE id = 42
```

**Reschedule:**
```sql
UPDATE appointments 
SET appointment_date = '2026-01-18', 
    appointment_time = '14:00', 
    status = 'scheduled',
    updated_at = NOW()
WHERE id = 42
```

**Interview Q: Why keep cancelled appointments instead of deleting?**
> **Audit trail.** We can analyze cancellation patterns, prevent abuse, and maintain history for medical records.

---

## 4. Data Privacy & Security

### 4.1 Password Storage (Current: INSECURE)

**Current Implementation:**
```python
# Registration
user_data["password"] = request.form.get("password")  # Plain text!

# Login
if user["password"] == password:  # Direct comparison
```

**Problem:** Passwords stored as plain text. If database is compromised, all passwords are exposed.

**Correct Implementation (what you should know for interview):**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Registration
user_data["password"] = generate_password_hash(password)  # Hashed!

# Login  
if check_password_hash(user["password"], password):  # Safe comparison
```

**Interview Q: How does password hashing work?**
> 1. Hash function (bcrypt/argon2) converts password to fixed-length string
> 2. **Salt** (random data) added to prevent rainbow table attacks
> 3. Result: `pbkdf2:sha256:260000$salt$hash`
> 4. On login: hash the input, compare with stored hash

---

### 4.2 Patient Data Privacy

**How patient data is kept private:**

| Protection | Implementation |
|-----------|----------------|
| **Authentication** | Session-based login required for all patient routes |
| **Authorization** | Route checks `session["user"]["role"]` and ownership |
| **Data Isolation** | Queries filter by `patient_id` or `patient_email` |

**Example Authorization Check:**
```python
@app.route("/patient/dashboard")
def patient_dashboard():
    # Check 1: User must be logged in
    if "user" not in session:
        return redirect(url_for("login"))
    
    # Check 2: User must be a patient (not doctor accessing patient route)
    if session["user"]["role"] != "patient":
        return redirect(url_for("login"))
    
    # Check 3: Only load THIS patient's data
    consultations = load_patient_consultations(session["user"]["email"])
    appointments = get_patient_appointments(session["user"]["id"])
```

**Database-Level Isolation:**
```sql
-- Patient can only see their own consultations
SELECT * FROM consultations WHERE patient_email = 'logged_in_user@email.com'

-- Patient can only see their own appointments
SELECT * FROM appointments WHERE patient_id = 5  -- logged-in user's ID
```

**Interview Q: Can one patient see another patient's data?**
> No. Every query includes a WHERE clause filtering by the logged-in user's ID/email. The application layer enforces this.

---

### 4.3 Doctor Access to Patient Data

Doctors have broader access but still controlled:

```python
@app.route("/doctor/reply/<int:consultation_id>")
def doctor_reply(consultation_id):
    # Check: Must be logged in as doctor
    if session["user"]["role"] != "doctor":
        return redirect(url_for("doctor_login"))
    
    # Doctor can view any consultation (part of their job)
    consultation = get_consultation_by_id(consultation_id)
```

**Interview Q: What's the difference between patient and doctor access?**
| Data | Patient Access | Doctor Access |
|------|---------------|---------------|
| Own consultations | ✅ Read | ✅ Read + Reply |
| Other patients' consultations | ❌ | ✅ (for treatment) |
| Own appointments | ✅ CRUD | N/A |
| All appointments | ❌ | ✅ Their schedule |
| Availability | ❌ | ✅ Manage own |

---

### 4.4 Media File Privacy

**Google Drive files are protected by:**
1. **Database ownership check** before streaming:
```python
@app.route("/drive/media/<int:media_id>")
def drive_media(media_id):
    media = get_consultation_media(media_id)
    consultation = get_consultation_by_id(media['consultation_id'])
    
    # Authorization check
    if role == "patient":
        if consultation['patient_email'] != session["user"]["email"]:
            abort(403)  # Forbidden
```

2. **No direct Drive URLs** exposed to users — files streamed through server

---

## 5. Transaction Handling

### 5.1 What is a Transaction?

A transaction is a sequence of operations that either **all succeed** or **all fail** (atomicity).

**Pattern used in this project:**
```python
def save_appointment(appointment_data):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO appointments ...")
        conn.commit()  # ✅ Success: save changes
        return True
    except Exception as e:
        conn.rollback()  # ❌ Failure: undo changes
        return False
    finally:
        conn.close()
```

**Interview Q: What happens if the server crashes after INSERT but before COMMIT?**
> The transaction is **rolled back** automatically. The data is not saved. This is **atomicity** — all or nothing.

---

### 5.2 Implicit vs Explicit Transactions

| Type | SQLite | PostgreSQL |
|------|--------|------------|
| Auto-commit | Default ON | Default ON |
| Explicit | `BEGIN; ... COMMIT;` | `BEGIN; ... COMMIT;` |
| This project | Uses `conn.commit()` after each operation | Same |

---

## 6. Common DBMS Interview Questions (with Answers)

### Q1: Explain normalization. Is your database normalized?

**Answer:**
Normalization removes data redundancy. Our database is **partially normalized**:

| Table | Normalization Status |
|-------|---------------------|
| users | ✅ Fully normalized (3NF) |
| consultations | ⚠️ Denormalized: `patient_name` duplicated (should just use email FK) |
| doctor_availability | ⚠️ Denormalized: slot columns instead of separate rows |
| consultation_media | ✅ Normalized with proper FKs |

**Why denormalize?**
- Query performance (avoid JOINs)
- Simpler code
- Trade-off: data duplication, update anomalies

---

### Q2: What are the foreign keys in your schema?

```
consultations.patient_email    → users.email
consultation_media.consultation_id → consultations.id (ON DELETE CASCADE)
consultation_media.patient_email   → users.email
appointments.patient_id        → users.id
appointments.doctor_id         → users.id
doctor_availability.doctor_id  → users.id
site_notices.doctor_id         → users.id
```

---

### Q3: Explain CASCADE DELETE.

**Answer:**
When a parent row is deleted, child rows are automatically deleted.

```sql
-- consultation_media has: ON DELETE CASCADE
-- If we delete a consultation:
DELETE FROM consultations WHERE id = 42;
-- All rows in consultation_media WHERE consultation_id = 42 are AUTO-DELETED
```

**Interview Q: What's NOT deleted automatically?**
> Google Drive files! The database row is deleted, but the actual file remains in Drive. We handle this in application code by calling `DRIVE_STORAGE.delete_file_permanently()` first.

---

### Q4: How would you add indexing to improve performance?

**Recommended indexes:**
```sql
-- Speed up patient's consultation list
CREATE INDEX idx_consultations_patient_email ON consultations(patient_email);

-- Speed up doctor's appointment calendar
CREATE INDEX idx_appointments_doctor_date ON appointments(doctor_id, appointment_date);

-- Speed up slot availability check
CREATE INDEX idx_appointments_slot ON appointments(doctor_id, appointment_date, appointment_time);

-- Speed up login
CREATE INDEX idx_users_email ON users(email);  -- Already UNIQUE, so indexed
```

**Interview Q: When NOT to add an index?**
> - Small tables (full scan is fast)
> - Columns with low cardinality (e.g., `status` with only 3 values)
> - Tables with heavy INSERT/UPDATE (indexes slow writes)

---

### Q5: Explain ACID properties with examples from your project.

| Property | Meaning | Example |
|----------|---------|---------|
| **Atomicity** | All or nothing | Booking fails → no partial appointment saved |
| **Consistency** | Data stays valid | UNIQUE email constraint prevents duplicate accounts |
| **Isolation** | Concurrent transactions don't interfere | Two patients booking same slot handled (ideally with locks) |
| **Durability** | Committed data survives crashes | After `conn.commit()`, data is on disk |

---

### Q6: What is SQL injection? Is your app vulnerable?

**SQL Injection:** Attacker inserts malicious SQL through user input.

**Vulnerable code (NOT in our project):**
```python
# DANGEROUS!
query = f"SELECT * FROM users WHERE email = '{email}'"
```

If `email = "'; DROP TABLE users; --"`, the query becomes:
```sql
SELECT * FROM users WHERE email = ''; DROP TABLE users; --'
```

**Our project uses parameterized queries (SAFE):**
```python
cur.execute("SELECT * FROM users WHERE email = ?", (email,))
# The ? is replaced safely, special characters escaped
```

---

### Q7: How would you implement soft delete?

**Current: Hard delete**
```sql
DELETE FROM consultations WHERE id = 42  -- Gone forever
```

**Soft delete: Add `deleted_at` column**
```sql
-- Instead of DELETE:
UPDATE consultations SET deleted_at = NOW() WHERE id = 42

-- All queries add:
SELECT * FROM consultations WHERE deleted_at IS NULL
```

**Benefits:** Data recovery, audit trail, referential integrity preserved

---

## 7. Sample SQL Queries You Should Know

### 7.1 List all pending consultations with patient details
```sql
SELECT c.id, c.symptoms, c.created_at, u.name, u.email, u.phone
FROM consultations c
JOIN users u ON c.patient_email = u.email
WHERE c.status = 'pending'
ORDER BY c.created_at ASC;
```

### 7.2 Count appointments per doctor per day
```sql
SELECT doctor_id, appointment_date, COUNT(*) as appointment_count
FROM appointments
WHERE status = 'scheduled'
GROUP BY doctor_id, appointment_date
ORDER BY appointment_date;
```

### 7.3 Find fully booked slots for a date
```sql
SELECT appointment_time, COUNT(*) as booked
FROM appointments
WHERE doctor_id = 1 
  AND appointment_date = '2026-01-15'
  AND status = 'scheduled'
GROUP BY appointment_time
HAVING COUNT(*) >= 15;  -- MAX_PATIENTS_PER_SLOT
```

### 7.4 Patient's complete history (consultations + appointments)
```sql
-- Using UNION for combined timeline
SELECT 'consultation' as type, id, symptoms as details, created_at
FROM consultations WHERE patient_email = 'john@email.com'
UNION ALL
SELECT 'appointment' as type, id, reason as details, created_at
FROM appointments WHERE patient_id = 5
ORDER BY created_at DESC;
```

### 7.5 Cancellation rate by month
```sql
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
    ROUND(100.0 * SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) as cancel_rate
FROM appointments
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;
```

---

## 8. Quick Reference: File Locations

| File | Purpose |
|------|---------|
| `app/database.py` | PostgreSQL functions (production) |
| `app/database_local.py` | SQLite functions (development) |
| `app/main.py` | Routes that call database functions |
| `app/models.py` | SQLAlchemy model (legacy, not actively used) |
| `homeopathy.db` | SQLite database file (local) |

---

## 9. Interview Tips

1. **Always mention trade-offs** — "We denormalized X for performance, trade-off is data duplication"

2. **Know your constraints** — UNIQUE, NOT NULL, FOREIGN KEY, CHECK

3. **Explain your JOIN types** — This project uses INNER JOINs mostly

4. **Security awareness** — Acknowledge the plaintext password issue and explain proper hashing

5. **Be ready to improve** — "I would add indexes on X, Y columns for the doctor dashboard query"

6. **Transactions matter** — Explain commit/rollback and when they're needed

7. **Scale considerations** — "For more users, I'd add connection pooling and read replicas"
