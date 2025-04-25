"""
FarmPi5 Greenhouse Control System - GPIO Control Module
Author: Jason Hackett, Bucknell Senior Design Team 2025
Date: April 6, 2025

This module manages GPIO initialization and control for the shutter motors
and LED indicators. It provides centralized motor tracking and visual feedback
through LED sequences.
"""

import sys
import time
import threading
import gpiod  # type: ignore
from management.logger import log_event
from management.config import SLUG_SHUTTER_PINS, SLUG_SIDEWALL_PINS, LED_PIN, motorControl

chip = None
gpio_lines = {}

def init_gpio():
    """
    Initialize the GPIO lines using gpiod.
    When motorControl is True, only the LED pin is initialized.
    When False, all output pins (motors + LED) are initialized.
    """
    global chip, gpio_lines
    try:
        chip = gpiod.Chip('gpiochip4')
    except Exception as e:
        log_event(f"ERROR: Could not open gpiochip4: {e}")
        sys.exit(1)
    
    if not motorControl:
        # Initialize only the LED pin for motor simulation
        try:
            gpio_lines[LED_PIN] = chip.get_line(LED_PIN)
            gpio_lines[LED_PIN].request(consumer="APP_OUT", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
            log_event("GPIO initialized for LED output in simulated motor control mode.")
        except Exception as e:
            log_event(f"ERROR: Could not initialize LED pin {LED_PIN}: {e}")
        return

    # Normal operation: Initialize all output pins.
    pins_needed = set()
    for mapping in (SLUG_SHUTTER_PINS, SLUG_SIDEWALL_PINS):
        for mapping_item in mapping.values():
            pins_needed.add(mapping_item["out_pin"])
    pins_needed.add(LED_PIN)
    
    for pin in pins_needed:
        try:
            gpio_lines[pin] = chip.get_line(pin)
            gpio_lines[pin].request(consumer="APP_OUT", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
        except Exception as e:
            log_event(f"ERROR: Could not initialize output for pin {pin}: {e}")

    log_event("GPIO initialized for output-only shutter control.")

# --- Global variables for centralized LED control ---
active_motor_count = 0
active_motor_lock = threading.Lock()
led_stop_timer = None

def led_start_sequence():
    """
    Trigger a flash sequence and leave the LED ON.
    This is called when the first motor operation begins.
    """
    led_line = gpio_lines.get(LED_PIN)
    if not led_line:
        log_event("ERROR: LED pin not available for start sequence.")
        return
    # Flash LED 5 times quickly (no cancel checks)
    for _ in range(5):
        time.sleep(0.2)
        led_line.set_value(0)
        time.sleep(0.2)
        led_line.set_value(1)
    # Ensure LED stays on
    led_line.set_value(1)
    log_event("Global LED start sequence completed; LED is now ON.")

def led_stop_sequence():
    """
    Trigger a slow blink sequence and then turn the LED OFF.
    This is called when the last motor operation finishes.
    """
    led_line = gpio_lines.get(LED_PIN)
    if not led_line:
        log_event("ERROR: LED pin not available for stop sequence.")
        return
    # Slow blink LED 3 times
    for _ in range(3):
        led_line.set_value(0)
        time.sleep(0.5)
        led_line.set_value(1)
        time.sleep(0.5)
    led_line.set_value(0)
    log_event("Global LED stop sequence completed; LED is now OFF.")

def motor_started():
    """
    Increment active motor count atomically.
    If the count goes from 0 to 1, trigger the LED start sequence.
    """
    global active_motor_count, led_stop_timer
    with active_motor_lock:
        # Cancel any pending LED shutdown if a new motor starts
        if active_motor_count == 0 and led_stop_timer is not None:
            led_stop_timer.cancel()
            led_stop_timer = None
        active_motor_count += 1
        if active_motor_count == 1:
            led_start_sequence()

def motor_finished():
    """
    Decrement active motor count atomically.
    If the count drops to 0, trigger the LED stop sequence.
    """
    global active_motor_count, led_stop_timer
    with active_motor_lock:
        if active_motor_count > 0:
            active_motor_count -= 1
        if active_motor_count == 0:
            # Delay the LED shutdown by 2 seconds
            led_stop_timer = threading.Timer(2, led_stop_sequence)
            led_stop_timer.start()
