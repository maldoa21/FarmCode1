import time
from datetime import datetime, timedelta
from gpio.sensors import read_sensor_data
from gpio.shutters import operate_shutter
from management.logger import log_event

# Constants for automation settings
SIDEWALL_OPEN_SETPOINT = 75.0  # °F
SIDEWALL_CLOSE_SETPOINT = 70.0  # °F
SHUTTER_OPEN_SETPOINT = 65.0  # °F
SHUTTER_CLOSE_SETPOINT = 60.0  # °F

SHUTTER_IDLE_TIME = timedelta(minutes=1)  # Minimum time between movements
SIDEWALL_IDLE_TIME = timedelta(minutes=3)  # Minimum time between movements

SHUTTER_RUNTIME = 15  # Seconds
SIDEWALL_RUNTIME = 60  # Seconds

# Last operation timestamps
last_shutter_operation = None
last_sidewall_operation = None

def automate_shutters_and_sidewalls():
    """
    Automate the operation of shutters and sidewalls based on temperature.
    """
    global last_shutter_operation, last_sidewall_operation

    while True:
        try:
            # Read the current temperature
            data = read_sensor_data()
            if "error" in data:
                log_event(f"[ERROR] Failed to read sensor data: {data['error']}")
                time.sleep(5)  # Retry after 5 seconds
                continue

            temperature = data["temperature"]
            log_event(f"Current temperature: {temperature:.2f} °F")

            # Automate sidewall
            now = datetime.now()
            if temperature >= SIDEWALL_OPEN_SETPOINT:
                if last_sidewall_operation is None or now - last_sidewall_operation >= SIDEWALL_IDLE_TIME:
                    log_event("Temperature exceeds sidewall open setpoint. Opening sidewall.")
                    operate_shutter("Slug Sidewall", "open")
                    last_sidewall_operation = now
                    time.sleep(SIDEWALL_RUNTIME)
            elif temperature <= SIDEWALL_CLOSE_SETPOINT:
                if last_sidewall_operation is None or now - last_sidewall_operation >= SIDEWALL_IDLE_TIME:
                    log_event("Temperature below sidewall close setpoint. Closing sidewall.")
                    operate_shutter("Slug Sidewall", "close")
                    last_sidewall_operation = now
                    time.sleep(SIDEWALL_RUNTIME)

            # Automate shutter
            if temperature >= SHUTTER_OPEN_SETPOINT:
                if last_shutter_operation is None or now - last_shutter_operation >= SHUTTER_IDLE_TIME:
                    log_event("Temperature exceeds shutter open setpoint. Opening shutter.")
                    operate_shutter("Slug Shutter", "open")
                    last_shutter_operation = now
                    time.sleep(SHUTTER_RUNTIME)
            elif temperature <= SHUTTER_CLOSE_SETPOINT:
                if last_shutter_operation is None or now - last_shutter_operation >= SHUTTER_IDLE_TIME:
                    log_event("Temperature below shutter close setpoint. Closing shutter.")
                    operate_shutter("Slug Shutter", "close")
                    last_shutter_operation = now
                    time.sleep(SHUTTER_RUNTIME)

            # Sleep for a short interval before checking again
            time.sleep(5)

        except Exception as e:
            log_event(f"[ERROR] Exception in automation loop: {e}")
            time.sleep(5)  # Retry after 5 seconds
