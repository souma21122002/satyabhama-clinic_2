import sqlite3

DB_FILE = "homeopathy.db"

def fix_availability_table():
    """Drop old table and create new one"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        print("🔧 Dropping old doctor_availability table...")
        cursor.execute("DROP TABLE IF EXISTS doctor_availability")
        
        print("🔧 Creating new doctor_availability table...")
        cursor.execute("""
            CREATE TABLE doctor_availability (
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
        print("✅ Doctor availability table fixed successfully!")
        print("   You can now set availability by date.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_availability_table()
