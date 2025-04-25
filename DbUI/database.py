from management.logger import log_event
from management.config import DB_FILE
import sqlite3

def init_db():
    """
    Initialize the shutter database with shutters and logs tables.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            # Drop existing table if it exists
            c.execute('DROP TABLE IF EXISTS shutters')
            
            # Recreate with updated constraint including 'live'
            c.execute('''
                CREATE TABLE IF NOT EXISTS shutters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL CHECK(name IN ('Slug Sidewall', 'Slug Shutter')),
                    status TEXT NOT NULL CHECK(status IN ('open', 'closed', 'automatic', 'live'))
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event TEXT NOT NULL
                )
            ''')
            # Initialize default values
            c.execute("INSERT INTO shutters (name, status) VALUES ('Slug Sidewall', 'automatic')")
            c.execute("INSERT INTO shutters (name, status) VALUES ('Slug Shutter', 'automatic')")
            conn.commit()
        log_event("Database initialized with updated schema.")
    except Exception as e:
        log_event(f"ERROR: Database initialization failed: {e}")

def update_shutter_status(shutter_name: str, new_status: str):
    """
    Update shutter status in the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE shutters SET status = ? WHERE name = ?", (new_status, shutter_name))
            conn.commit()
        log_event(f"Database: Shutter '{shutter_name}' status updated to {new_status}.")
    except Exception as e:
        log_event(f"ERROR: Database update failed for {shutter_name}: {e}")

def get_shutter_status(shutter_name: str) -> str:
    """
    Retrieve the current status of a shutter from the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT status FROM shutters WHERE name = ?", (shutter_name,))
            result = c.fetchone()
            if result:
                return result[0]
            return "unknown"
    except Exception as e:
        log_event(f"ERROR: Could not retrieve status for {shutter_name}: {e}")
        return "error"