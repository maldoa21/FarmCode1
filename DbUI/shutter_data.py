
from flask import Blueprint, render_template
from datetime import datetime, timedelta
import sqlite3
from management.config import DB_FILE  # update path as needed
from management.logger import log_event

shutter_data = Blueprint("shutter_data", __name__)

@shutter_data.route("/shutter-data")
def view_full_log():
    all_logs = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT timestamp, event FROM logs ORDER BY timestamp DESC")
            all_logs = c.fetchall()
    except Exception as e:
        log_event(f"[ERROR] Failed to fetch logs from database: {e}")
        all_logs = []

    # Separate logs into shutter logs and temperature logs
    logs = []
    temperature_logs = []

    for ts, event in all_logs:
        if "temperature" in event.lower():
            temperature_logs.append((ts, event.split(":")[-1].strip()))
        else:
            logs.append((ts, event))

    # Filter shutter logs from last 24 hours
    last_24_hours_logs = []
    now = datetime.now()
    for ts, event in logs:
        try:
            log_time = datetime.strptime(ts, "%Y-%m-%d %I:%M %p")
            if now - log_time <= timedelta(hours=24):
                last_24_hours_logs.append((ts, event))
        except Exception as e:
            log_event(f"[WARNING] Failed to parse timestamp '{ts}': {e}")

    return render_template(
        "shutter_log.html",
        logs=logs,
        temperature_logs=temperature_logs,
        last_24_hours_logs=last_24_hours_logs
    )
