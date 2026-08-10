import sqlite3
from pathlib import Path
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DATABASE_URL

def migrate():
    # Parse db path from url "sqlite:///akshara.db"
    if not DATABASE_URL.startswith("sqlite:///"):
        print("Only sqlite migration is supported.")
        return
        
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist to avoid errors
    cursor.execute("PRAGMA table_info(audio_files)")
    columns = [info[1] for info in cursor.fetchall()]
    
    queries = []
    if "original_transcript" not in columns:
        queries.append("ALTER TABLE audio_files ADD COLUMN original_transcript TEXT")
    if "english_translation" not in columns:
        queries.append("ALTER TABLE audio_files ADD COLUMN english_translation TEXT")
    if "metadata_json" not in columns:
        queries.append("ALTER TABLE audio_files ADD COLUMN metadata_json TEXT")
        
    for q in queries:
        print(f"Executing: {q}")
        cursor.execute(q)
        
    conn.commit()
    conn.close()
    print("Migration successful.")

if __name__ == "__main__":
    migrate()
