import time
import datetime
import json
import threading
from management.config import LOG_FILE

LOG_LOCK = threading.Lock()

def log_event(event: str):
    """
    Append a log event as a JSON entry to the log file and print it to the console.
    """
    entry = {"timestamp": time.time(), "event": event}
    with LOG_LOCK:
        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[ERROR] Logging event failed: {e}")
    print(f"[LOG] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {event}")
