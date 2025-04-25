"""
FarmPi5 Greenhouse Control System - Sensor Monitoring Module
Author: Jason Hackett, Bucknell Senior Design Team 2025
Date: April 9, 2025

This script reads temperature and humidity data from a Modbus RTU device
connected via RS485 using the Waveshare RS485 CAN HAT. It uses MinimalModbus
for more reliable communication with half-duplex RS485 devices.
"""

import time
import minimalmodbus  # type: ignore[import]
from management.logger import log_event
from management.config import stop_event, MODBUS_PORT

# Global instrument instance for reuse
instrument = None

def get_modbus_instrument():
    """
    Get or create a MinimalModbus instrument instance.
    
    Returns:
        minimalmodbus.Instrument: Configured Modbus instrument
    """
    global instrument
    
    if instrument is None:
        try:
            # Create a new Modbus instrument
            # slave_address=9: The slave/unit address of the sensor
            mb_address = 1  # Modbus address of sensor
            instrument = minimalmodbus.Instrument(MODBUS_PORT, mb_address)
            
            # Configure serial settings
            instrument.serial.baudrate = 9600
            instrument.serial.bytesize = 8
            instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
            instrument.serial.stopbits = 1
            instrument.serial.timeout = 0.5
            
            # Set the mode explicitly (RTU or ASCII)
            instrument.mode = minimalmodbus.MODE_RTU
            
            # Critical settings for RS485 half-duplex communication
            # Good practice to clean up before and after each execution
            instrument.clear_buffers_before_each_transaction = True
            instrument.close_port_after_each_call = True
            
            # Debug mode: Set to True during troubleshooting
            instrument.debug = False
            
            log_event(f"Modbus instrument initialized on {MODBUS_PORT}")
        except Exception as e:
            log_event(f"Failed to initialize Modbus instrument: {e}")
            instrument = None
    
    return instrument

def read_sensor_data():
    """
    Reads temperature and humidity data from the Modbus device.
    
    Returns:
        dict: A dictionary with temperature and humidity values,
              or an error message if something went wrong.
    """
    try:
        # Get or create the instrument
        instr = get_modbus_instrument()
        if instr is None:
            return {"error": f"Unable to initialize Modbus device on {MODBUS_PORT}"}
        
        # Add a small delay to ensure RS485 transceiver is ready
        time.sleep(0.05)
        
        # Get list of values from MULTIPLE registers
        # Arguments - (register start address, number of registers to read, function code)
        data = instr.read_registers(0, 2, 3)
        
        # Process the raw data by dividing by 10 to get the actual floating point values
        # Note: In this sensor, register 0 is humidity and register 1 is temperature
        humidity = data[1] / 100.0
        temperature = (9 * data[0] / 500.0) + 32
        
        return {
            "temperature": temperature,
            "humidity": humidity
        }
    
    except minimalmodbus.NoResponseError as e:
        log_event(f"No response from Modbus device: {e}")
        return {"error": f"No response from device: {e}"}
    
    except minimalmodbus.InvalidResponseError as e:
        log_event(f"Invalid response from Modbus device: {e}")
        return {"error": f"Invalid response: {e}"}
    
    except Exception as e:
        log_event(f"Unexpected error reading sensor data: {e}")
        return {"error": f"Unexpected error: {e}"}

def monitor_sensors():
    """
    Continuously monitor sensors and print readings.
    Checks for the stop_event flag for graceful shutdown.
    """
    log_event("Starting continuous sensor monitoring...")
    retry_count = 0
    max_retries = 3
    retry_delay = 5  # seconds
    
    try:
        while not stop_event.is_set():
            # Read sensor data
            data = read_sensor_data()
            
            if "error" in data:
                print(f"Error: {data['error']}")
                # Implement retry logic with backoff
                retry_count += 1
                if retry_count > max_retries:
                    log_event(f"Exceeded maximum retries ({max_retries}). Waiting longer before next attempt.")
                    time.sleep(retry_delay * 2)  
                    retry_count = 0  # Reset counter
                else:
                    time.sleep(retry_delay)
            else:
                # Reset retry counter on success
                retry_count = 0
                
                temp = data["temperature"]
                humidity = data["humidity"]
                print(f"Temperature: {temp:.1f}°F, Humidity: {humidity:.1f}%")
                
                # Normal monitoring interval
                time.sleep(3)
    
    except Exception as e:
        log_event(f"Error in sensor monitoring: {e}")
    finally:
        # Clean up resources
        global instrument
        if instrument is not None:
            try:
                instrument.serial.close()
            except:
                pass
            instrument = None
        log_event("Sensor monitoring stopped")

# For standalone testing
if __name__ == "__main__":
    # For demonstration purposes - run continuous monitoring
    monitor_sensors()
