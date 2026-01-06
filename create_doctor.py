import os
import sys

# Determine environment
if os.getenv("FLASK_ENV") == "production":
    from app.database import save_user, get_user
else:
    from app.database_local import save_user, get_user

def create_default_doctor():
    """Create default doctor account"""
    doctor_email = "doctor@homeopathy.com"
    
    # Check if doctor already exists
    existing = get_user(doctor_email)
    if existing:
        print(f"✅ Doctor account already exists: {doctor_email}")
        return True
    
    # Create doctor account
    doctor_data = {
        "name": "Dr. Ajoy Kumar Singha Mahapatra",
        "email": doctor_email,
        "password": "doctor123",
        "phone": "+919932199936",
        "age": 35,
        "gender": "male",
        "role": "doctor"
    }
    
    if save_user(doctor_data):
        print(f"✅ Doctor account created successfully!")
        print(f"   Email: {doctor_email}")
        print(f"   Password: doctor123")
        return True
    else:
        print(f"❌ Failed to create doctor account")
        return False

if __name__ == "__main__":
    create_default_doctor()
