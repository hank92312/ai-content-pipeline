import sqlite3
import os

db_path = 'auto_channel.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE DailyNews ADD COLUMN content TEXT")
    conn.commit()
    print("✅ Migration successful: Added 'content' column to 'DailyNews' table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ Migration skipped: 'content' column already exists.")
    else:
        print(f"❌ Migration failed: {e}")
finally:
    conn.close()
