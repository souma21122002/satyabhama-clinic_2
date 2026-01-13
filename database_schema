# Homeopathy Project — Database Schema (SQLite dev / Postgres prod)

Source of truth: `init_db()` in `app/database_local.py` (SQLite) and `app/database.py` (Postgres).

## Notes
- Local/dev uses **SQLite** (`homeopathy.db`).
- Production uses **PostgreSQL** (`DATABASE_URL`).
- Key difference: `consultations.doctor_reply` is **TEXT (SQLite)** vs **JSONB (Postgres)**.

---

## Table: `users`

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK | Auto-increment identity |
| name | TEXT | VARCHAR(255) | NO |  |  |
| email | TEXT | VARCHAR(255) | NO | UNIQUE | Used as login + referenced by consultations |
| password | TEXT | VARCHAR(255) | NO |  | Stored as plaintext in current code (should be hashed) |
| phone | TEXT | VARCHAR(50) | YES |  |  |
| age | INTEGER | INTEGER | YES |  |  |
| gender | TEXT | VARCHAR(20) | YES |  |  |
| role | TEXT | VARCHAR(20) | YES | DEFAULT 'patient' | `patient` or `doctor` |
| doctor_notes | TEXT | TEXT | YES |  | Notes written by doctor |
| notes_updated | TIMESTAMP | TIMESTAMP | YES |  |  |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |

---

## Table: `consultations`

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| patient_email | TEXT | VARCHAR(255) | NO | FK → users(email) | Patient identity stored by email |
| patient_name | TEXT | VARCHAR(255) | NO |  | Denormalized snapshot |
| symptoms | TEXT | TEXT | NO |  | Main input text |
| duration | TEXT | VARCHAR(100) | YES |  |  |
| severity | TEXT | VARCHAR(50) | YES |  |  |
| medical_history | TEXT | TEXT | YES |  |  |
| current_medications | TEXT | TEXT | YES |  |  |
| voice_record | TEXT | VARCHAR(255) | YES |  | Legacy local upload filename |
| images | TEXT | TEXT | YES |  | JSON array stored as string (legacy) |
| documents | TEXT | TEXT | YES |  | JSON array stored as string (legacy) |
| status | TEXT | VARCHAR(20) | YES | DEFAULT 'pending' | `pending` / `replied` |
| doctor_reply | TEXT | JSONB | YES |  | Reply payload (diagnosis, remedies, etc.) |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |

---

## Table: `consultation_media`

Used when Google Drive storage is enabled. Rows are deleted automatically when a consultation is deleted.

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| consultation_id | INTEGER | INTEGER | NO | FK → consultations(id) ON DELETE CASCADE |  |
| patient_email | TEXT | VARCHAR(255) | NO | FK → users(email) |  |
| drive_file_id | TEXT | TEXT | NO |  | Google Drive file id |
| file_name | TEXT | TEXT | NO |  |  |
| mime_type | TEXT | TEXT | YES |  |  |
| media_type | TEXT | VARCHAR(20) | NO |  | e.g. `audio`, `image`, `video`, `pdf` |
| size_bytes | INTEGER | BIGINT | YES |  |  |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |

Indexes:
- `idx_consultation_media_consultation_id` on `(consultation_id)`
- `idx_consultation_media_patient_email` on `(patient_email)`

---

## Table: `case_history`

Stores symptom searches and suggested remedies (used by the remedy matcher history page).

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| symptoms | TEXT | TEXT | NO |  |  |
| suggested_remedies | TEXT | TEXT | YES |  |  |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |

---

## Table: `appointments`

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| patient_id | INTEGER | INTEGER | NO | FK → users(id) |  |
| doctor_id | INTEGER | INTEGER | NO | FK → users(id) |  |
| appointment_date | DATE | DATE | NO |  |  |
| appointment_time | TIME | TIME | NO |  |  |
| duration | INTEGER | INTEGER | YES | DEFAULT 30 | Minutes |
| status | TEXT | VARCHAR(20) | YES | DEFAULT 'scheduled' | `scheduled`/`completed`/`cancelled` |
| reason | TEXT | TEXT | YES |  |  |
| notes | TEXT | TEXT | YES |  | Present in Postgres DDL; in SQLite it may exist depending on version |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |
| updated_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |
| cancelled_at | TIMESTAMP | TIMESTAMP | YES |  |  |
| cancellation_reason | TEXT | TEXT | YES |  |  |

---

## Table: `doctor_availability`

This is date-wise availability with fixed time-slot columns.

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| doctor_id | INTEGER | INTEGER | NO | FK → users(id) |  |
| availability_date | DATE | DATE | NO |  |  |
| slot_09 | INTEGER | INTEGER | YES | DEFAULT 0 | 1 = enabled |
| slot_10 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_11 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_12 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_13 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_18 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_19 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_20 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_21 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| slot_22 | INTEGER | INTEGER | YES | DEFAULT 0 |  |
| is_off_day | INTEGER | BOOLEAN | YES | DEFAULT 0/FALSE | If true, all slots treated disabled |
| off_day_reason | TEXT | TEXT | YES |  |  |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |

Constraints:
- `UNIQUE(doctor_id, availability_date)`

---

## Table: `site_notices`

| Column | Type (SQLite) | Type (Postgres) | Null | Key/Default | Notes |
|---|---|---|---|---|---|
| id | INTEGER | SERIAL | NO | PK |  |
| doctor_id | INTEGER | INTEGER | YES | FK → users(id) | Nullable: system-wide notices |
| title | TEXT | VARCHAR(255) | NO |  |  |
| message | TEXT | TEXT | NO |  |  |
| is_active | INTEGER | BOOLEAN | YES | DEFAULT 1/TRUE |  |
| created_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |
| updated_at | TIMESTAMP | TIMESTAMP | YES | DEFAULT CURRENT_TIMESTAMP |  |
