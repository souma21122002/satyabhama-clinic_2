#!/bin/bash
set -e
pip install -r requirements.txt
python << 'EOF'
from app.database import init_db, save_user, get_user
init_db()

# Create default doctor
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
    print("✅ Default doctor account created")
else:
    print("✅ Doctor account already exists")
EOF
