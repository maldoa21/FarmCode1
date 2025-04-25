"""
FarmPi5 Greenhouse Control System - Configuration Module
Author: Jason Hackett, Bucknell Senior Design Team 2025
Date: April 6, 2025

This module defines system-wide configuration constants including
GPIO pin mappings, communication settings, database paths, and
shared resources like the global stop event for graceful shutdown.
"""

import threading

# Run 'lsusb' to get the USB device ID for the sensors
# or run 'dmesg | grep -i tty' to find the connected USB device.
# USB: '/dev/ttyUSB0' /1' or '/dev/ttyACM0' /1' or '/dev/ttyAMA0' /1'
# Serial: '/dev/serial0' /1'

# Run sudo raspi-config to enable the serial interface.
# Run sudo apt install python3-pymodbus to install pymodbus.


# Sensor modbus port for temperature and humidity readings.
MODBUS_PORT = "/dev/ttyUSB0" #/dev/ttyUSB0 for usb converter /dev/serial0 was here

# GPIO pins on or off for motor control. True means motor (GPIO) control is active.
motorControl = True

# Shutter GPIO mapping: only output pins are now used.
SLUG_SHUTTER_PINS = {
    "open": {"out_pin": 4},  # 5
    "close": {"out_pin": 17},  # 11
}
SLUG_SIDEWALL_PINS = {
    "open": {"out_pin": 27},  # 13
    "close": {"out_pin": 22},  # 15
}

LED_PIN = 5                   # LED for pre-/post-operation indication
MOTOR_RUNTIME = 15            # seconds the motor must stay HIGH exactly


# Temperature thresholds for automatic control (in Celsius)
LOWER_TEMP = 18  # Below this, shutters will close
HIGHER_TEMP = 30  # Above this, shutters will open
AUTO_CHECK_INTERVAL = 600  # Check every 10 minutes (600 seconds)


# Database and log configuration.
DB_FILE = "shutters_control.db"
LOG_FILE = "logged_data.json"

# Global stop event – used by threads for graceful shutdown.
stop_event = threading.Event()

# Pi GPIO UART pins.
"""
RS485 UART transmit: GPIO 14 (TXD) - Pin 8
RS485 UART receive: GPIO 15 (RXD) - Pin 10
Uses 3.3V logic level
Turn on UART on Raspberry Pi using `sudo raspi-config` and enable the serial interface.
RSE (TX/RX control) is auto by default but high for TX and low for RX.
"""
