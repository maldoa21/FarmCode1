"""
FarmPi5 Greenhouse Control System - Shutter Operation Module
Author: Jason Hackett, Bucknell Senior Design Team 2025
Date: April 6, 2025

This module controls the shutter and sidewall motors via GPIO,
providing functions to open, close, and cancel operations.
"""

import threading
import time
from management.logger import log_event
from DbUI.database import update_shutter_status, get_shutter_status
from gpio.gpio_control import gpio_lines, motor_started, motor_finished
from management.config import (MOTOR_RUNTIME, SLUG_SHUTTER_PINS, SLUG_SIDEWALL_PINS, 
                               motorControl, stop_event, LOWER_TEMP, HIGHER_TEMP, AUTO_CHECK_INTERVAL)
from gpio.sensors import read_sensor_data

# Existing data structures
operation_threads = {}          # device -> Thread
operation_cancel_flags = {}     # device -> threading.Event
operation_threads_lock = threading.Lock()
operation_intended_actions = {} # device -> intended action (open/close)

# New data structures for automatic mode
auto_mode_threads = {}          # device -> Thread
auto_mode_stop_flags = {}       # device -> threading.Event
auto_mode_lock = threading.Lock()

def get_temperature() -> float:
    """Fetch the latest temperature from the sensor."""
    try:
        data = read_sensor_data()  # Use the function from sensors.py
        if "error" in data:
            log_event(f"[ERROR] Failed to fetch temperature: {data['error']}")
            return 0.0
        temperature = data["temperature"]
        log_event(f"Temperature fetched from sensor: {temperature:.2f} °F")
        return round(temperature, 2)
    except Exception as e:
        log_event(f"[ERROR] Exception in get_temperature: {e}")
        return 0.0

def determine_automatic_action(device, temperature):
    """
    Determine what action to take based on current temperature.
    
    Args:
        device: The device name (e.g., "Slug Shutter")
        temperature: Current temperature in Fahrenheit
        
    Returns:
        action: "open", "close", or None
    """
    if temperature is None:
        log_event(f"Cannot determine automatic action: No temperature data")
        return None
        
    if temperature > HIGHER_TEMP:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°F > {HIGHER_TEMP}°F")
        return "open"
    elif temperature < LOWER_TEMP:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°F < {LOWER_TEMP}°F")
        return "close"
    else:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°F is within range - Monitoring continues")
        return None

def automatic_control_thread(device, stop_flag):
    """
    Thread function for automatic control of a device.
    Continuously monitors temperature and keeps it within the range.
    
    Args:
        device: The device to control
        stop_flag: Event to signal when to stop the thread
    """
    log_event(f"Starting automatic control thread for {device}")
    
    while not stop_flag.is_set() and not stop_event.is_set():
        # Check current device status - if it's not "automatic" anymore, exit
        current_status = get_shutter_status(device)
        if current_status != "automatic":
            log_event(f"Automatic control stopped for {device}: no longer in automatic mode")
            break
            
        # Get current temperature and determine action
        temperature = get_temperature()
        action = determine_automatic_action(device, temperature)
        
        # Take action if needed
        if action in ["open", "close"]:
            log_event(f"Automatic control: Initiating {action} for {device}")
            operate_shutter(device, action)
            
            # After performing the action, ensure the device remains in "automatic" mode
            update_shutter_status(device, "automatic")
            log_event(f"Automatic control: Returned {device} to automatic mode after {action}")
        
        # Wait for next check interval or until stopped
        stop_flag.wait(AUTO_CHECK_INTERVAL)
    
    log_event(f"Automatic control thread for {device} is exiting")

def start_automatic_control(device):
    """
    Start automatic control for a device.
    
    Args:
        device: The device name to control automatically
    """
    with auto_mode_lock:
        # Stop any existing automatic control thread for this device
        if device in auto_mode_stop_flags:
            auto_mode_stop_flags[device].set()
        
        # Create a new stop flag
        stop_flag = threading.Event()
        auto_mode_stop_flags[device] = stop_flag
        
        # Create and start the thread
        thread = threading.Thread(
            target=automatic_control_thread,
            args=(device, stop_flag),
            daemon=True
        )
        auto_mode_threads[device] = thread
        thread.start()
        
        log_event(f"Automatic control started for {device}")

def stop_automatic_control(device):
    """
    Stop automatic control for a device.
    
    Args:
        device: The device name to stop controlling automatically
    """
    with auto_mode_lock:
        if device in auto_mode_stop_flags:
            auto_mode_stop_flags[device].set()
            log_event(f"Automatic control stopping for {device}")
        else:
            log_event(f"No automatic control to stop for {device}")

def operate_shutter(device: str, action: str):
    """
    Operate the shutter or sidewall for a given device and action.
    
    Args:
        device: The device name (e.g., "Slug Shutter")
        action: The action to perform ("open", "close", or "automatic")
    """
    # Handle automatic mode separately
    if action == "automatic":
        log_event(f"Setting {device} to automatic mode")
        update_shutter_status(device, "automatic")
        start_automatic_control(device)
        return

    # For non-automatic actions, stop any automatic control
    stop_automatic_control(device)

    # Perform the manual action
    log_event(f"Manual operation: {action.upper()} initiated for {device}")
    # Simulate or perform the actual motor operation here
    # (Implementation omitted for brevity)
    update_shutter_status(device, action)
    log_event(f"Manual operation: {action.upper()} completed for {device}")
