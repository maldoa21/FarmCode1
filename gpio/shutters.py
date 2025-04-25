"""
FarmPi5 Greenhouse Control System - Shutter Operation Module
Author: Jason Hackett, Bucknell Senior Design Team 2025
Date: April 6, 2025

This module controls the shutter and sidewall motors via GPIO,
providing functions to open, close, and cancel operations.
"""

import threading
import time
import asyncio
from management.logger import log_event
from DbUI.database import update_shutter_status, get_shutter_status
from gpio.gpio_control import gpio_lines, motor_started, motor_finished
from management.config import (MOTOR_RUNTIME, SLUG_SHUTTER_PINS, SLUG_SIDEWALL_PINS, 
                    motorControl, stop_event, LOWER_TEMP, HIGHER_TEMP, AUTO_CHECK_INTERVAL)
from gpio.sensors import read_sensor_data


# TODO: To allow update of temperature thresholds from the UI,
#       need to add a function to update the;
#       LOWER_TEMP, HIGHER_TEMP and AUTO_CHECK_INTERVAL values.
#       e.g. from DbUI.database import update_auto_mode, get_thresholds



# Existing data structures
operation_threads = {}          # device -> Thread
operation_cancel_flags = {}     # device -> threading.Event
operation_threads_lock = threading.Lock()
operation_intended_actions = {} # device -> intended action (open/close)

# New data structures for automatic mode
auto_mode_threads = {}          # device -> Thread
auto_mode_stop_flags = {}       # device -> threading.Event
auto_mode_lock = threading.Lock()

def get_current_temperature():
    """
    Get the current temperature from the sensor.
    Returns the temperature in Celsius or None if there's an error.
    """
    try:
        # Create a new event loop for this thread to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async function and get the result
        sensor_data = loop.run_until_complete(read_sensor_data())
        loop.close()
        
        if "error" in sensor_data:
            log_event(f"Error reading temperature: {sensor_data['error']}")
            return None
        
        temperature = sensor_data.get("temperature")
        log_event(f"Current temperature: {temperature:.2f}°C")
        return temperature
    except Exception as e:
        log_event(f"Exception while reading temperature: {e}")
        return None

def determine_automatic_action(device, temperature):
    """
    Determine what action to take based on current temperature.
    
    Args:
        device: The device name (e.g., "Slug Shutter")
        temperature: Current temperature in Celsius
        
    Returns:
        action: "open", "close", or None
    """
    if temperature is None:
        log_event(f"Cannot determine automatic action for {device}: No temperature data")
        return None
        
    if temperature > HIGHER_TEMP:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°C > {HIGHER_TEMP}°C - Opening {device}")
        return "open"
    elif temperature < LOWER_TEMP:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°C < {LOWER_TEMP}°C - Closing {device}")
        return "close"
    else:
        log_event(f"Automatic mode: Temperature {temperature:.2f}°C is within range - No action needed for {device}")
        return None

def automatic_control_thread(device, stop_flag):
    """
    Thread function for automatic control of a device.
    Checks temperature every AUTO_CHECK_INTERVAL seconds and takes action if needed.
    
    Args:
        device: The device to control
        stop_flag: Event to signal when to stop the thread
    """
    log_event(f"Starting automatic control for {device}")
    
    while not stop_flag.is_set() and not stop_event.is_set():
        # Check current device status - if it's not "automatic" anymore, exit
        current_status = get_shutter_status(device)
        if current_status != "automatic":
            log_event(f"Automatic control stopped: {device} is no longer in automatic mode")
            break
            
        # Get current temperature and determine action
        temperature = get_current_temperature()
        
        
        # TODO: Add a check if there are db updates to the temperature thresholds
        #       and update the HIGHER_TEMP and LOWER_TEMP values accordingly.
        #       Also, check if the AUTO_CHECK_INTERVAL has been updated.
        #       If so, update the AUTO_CHECK_INTERVAL value accordingly.
        
        action = determine_automatic_action(device, temperature)
        
        # Take action if needed
        if action in ["open", "close"]:
            # Don't take action if device is already in the desired state
            if current_status == action:
                log_event(f"Automatic control: {device} is already {action}")
            else:
                log_event(f"Automatic control: Initiating {action} for {device}")
                # Call operate_shutter with the determined action
                operate_shutter(device, action)
        
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
    mapping = None
    if device == "Slug Shutter":
        mapping = SLUG_SHUTTER_PINS
    elif device == "Slug Sidewall":
        mapping = SLUG_SIDEWALL_PINS
    
    # Handle automatic mode separately
    if action == "automatic":
        log_event(f"Setting {device} to automatic mode")
        update_shutter_status(device, "automatic")
        start_automatic_control(device)
        return

    # Check if mapping exists and action is valid for non-automatic actions
    if not mapping or action not in mapping:
        log_event(f"ERROR: Invalid device '{device}' or action '{action}'.")
        return

    # For non-automatic actions, stop any automatic control
    stop_automatic_control(device)

    # Create a cancellation flag and save it for the device.
    cancel_flag = threading.Event()
    with operation_threads_lock:
        # Set any existing flag to cancel the current operation.
        if device in operation_cancel_flags:
            operation_cancel_flags[device].set()
        operation_cancel_flags[device] = cancel_flag
        operation_intended_actions[device] = action

    # Simulation branch: when motorControl is False (simulation enabled)
    if not motorControl:
        log_event(f"SIMULATION: {action.upper()} operation initiated for {device}.")
        motor_started()
        try:
            time.sleep(MOTOR_RUNTIME)
            # If cancellation was requested, skip updating the status so that "live" remains.
            if cancel_flag.is_set():
                log_event(f"SIMULATION: Operation for {device} was cancelled; skipping final update.")
                return
            final_state = "closed" if action == "close" else action
            update_shutter_status(device, final_state)
            log_event(f"SIMULATION: {action.upper()} operation completed for {device}.")
        finally:
            motor_finished()
        return

    # For Manual GPIO control (motorControl is True)
    pins = mapping[action]
    out_pin = pins["out_pin"]
    out_line = gpio_lines.get(out_pin)
    if not out_line:
        log_event(f"ERROR: Could not access output line for {device}.")
        return

    def shutter_thread():
        try:
            log_event(f"START: {action.upper()} operation initiated for {device}.")
            motor_started()
            out_line.set_value(1)
            log_event(f"{device}: Motor (pin {out_pin}) set to HIGH for {action.upper()}.")

            # Use cancel_flag.wait() to replace time.sleep(MOTOR_RUNTIME)
            # This will return True if cancel_flag is set within the timeout.
            if cancel_flag.wait(MOTOR_RUNTIME):
                log_event(f"Operation for {device} was cancelled; stopping motor immediately.")
                out_line.set_value(0)
                return

            out_line.set_value(0)
            log_event(f"{device}: Motor (pin {out_pin}) set to LOW, ending {action.upper()} operation.")

            if cancel_flag.is_set():
                log_event(f"Operation for {device} was cancelled; skipping final update.")
                return

            final_state = "closed" if action == "close" else action
            update_shutter_status(device, final_state)
            log_event(f"COMPLETE: {action.upper()} operation completed for {device}.")
        except Exception as ex:
            log_event(f"ERROR: Exception in shutter operation for {device} during {action}: {ex}")
        finally:
            motor_finished()
            with operation_threads_lock:
                if device in operation_intended_actions:
                    del operation_intended_actions[device]
                if device in operation_cancel_flags and operation_cancel_flags[device] == cancel_flag:
                    del operation_cancel_flags[device]
    thread = threading.Thread(target=shutter_thread, daemon=True)
    with operation_threads_lock:
        operation_threads[device] = thread
    thread.start()

def cancel_shutter_operation(device: str):
    with operation_threads_lock:
        if device in operation_cancel_flags:
            operation_cancel_flags[device].set()
            log_event(f"Cancellation signal sent for {device}.")
        else:
            log_event(f"No operation to cancel for {device}.")
