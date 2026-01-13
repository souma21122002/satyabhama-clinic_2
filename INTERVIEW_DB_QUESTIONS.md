# Interview Questions — Database & SQL (Homeopathy Project)

These are realistic questions you can be asked based on this project’s database and flows.

## Schema / Design
- Why does `consultations` reference patients by `patient_email` instead of `patient_id`?
- What are the pros/cons of using `JSONB` (`doctor_reply`) vs normalized columns?
- The availability table uses `slot_09`, `slot_10`, etc. How would you redesign it to be normalized?
- How would you model “slot capacity” instead of using a hardcoded `MAX_PATIENTS_PER_SLOT` in code?
- What constraints would you add to prevent bad data (invalid roles, negative ages, etc.)?

## Joins & Reporting
- Get all upcoming appointments for a doctor with patient name/phone.
- Get all appointments for a patient with doctor details.
- Show daily appointment count per doctor for a month.
- Find patients with the most consultations.
- List pending consultations older than 48 hours.

## Aggregations
- Cancellation rate by month (cancelled / total).
- Peak booking hours (most booked `appointment_time`).
- Average number of consultations per patient.

## Indexing / Performance
- Which columns are your best candidates for indexing and why?
- Explain how an index on `(doctor_id, appointment_date)` helps doctor calendar queries.
- How would you optimize “search consultations by patient” and “list recent consultations”?

## Transactions / Concurrency
- Booking flow: how do you prevent exceeding capacity under concurrent requests?
- What isolation level would you choose for booking and why?

## Data Integrity / Cascades
- Why use `ON DELETE CASCADE` on `consultation_media.consultation_id`?
- What orphaned resources can still exist (e.g., Google Drive files) and how to reconcile them?

## Security
- What is wrong with storing plaintext passwords and how would you migrate to hashed passwords?
- How would you protect PII (emails/phone) at rest and in logs?

## Practical SQL Exercises (what you can be asked to write)
- Write a query to fetch available slots for a doctor on a date.
- Write a query to find fully booked slots for a date.
- Write a query to list all active site notices ordered by last update.
- (Postgres) Query JSONB: consultations where `doctor_reply` contains a certain field/value.
