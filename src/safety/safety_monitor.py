#!/usr/bin/env python
# coding: utf-8
"""Safety Monitor Thread implementation (ADR-009 Layer 3).

This module implements the 10Hz safety monitor that performs mode-dependent
checks for battery voltage, fault detection, and system health.

Safety Layers (ADR-009):
- Layer 1 (Hardware): ThunderBorg 250ms failsafe (handled by hardware)
- Layer 2 (Watchdog): 1 second timeout (see Watchdog in monsterWeb.py)
- Layer 3 (Safety Monitor): This module - 10Hz polling

Mode-Dependent Behavior:
- Manual Mode: Driver responsibility, stop on signal loss only
- Autonomous Mode: Mandatory battery/fault checks, stop on issues

Battery Thresholds:
- Stop (autonomous): 10.5V
- Warning (manual): 11.0V

Threading Priority (ADR-008):
- This runs at Tier 1 (Highest) priority, equal to Motor Control

See Also:
    - docs/DECISIONS.md: ADR-009 for safety system architecture
    - docs/DECISIONS.md: ADR-008 for threading model
    - config/config.json: safety section for thresholds
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

# Module logger for safety monitoring events
_logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Robot operation mode affecting safety behavior."""

    MANUAL = "manual"
    AUTONOMOUS = "autonomous"
    STOPPED = "stopped"


@dataclass
class SafetyStatus:
    """Current safety system status."""

    mode: OperationMode
    battery_voltage: float
    battery_ok: bool
    fault_detected: bool
    fault_message: str
    signal_ok: bool
    last_check: float


class SafetyMonitor(threading.Thread):
    """Safety monitor thread running at 10Hz (Tier 1 priority).

    Performs continuous safety checks based on operation mode:
    - MANUAL: Only checks for signal loss
    - AUTONOMOUS: Checks battery, faults, and signal

    This thread is non-daemon to ensure clean shutdown. The main program
    must call terminate() followed by join() during shutdown.

    Lock Acquisition Order:
        To prevent deadlocks, always acquire locks in this order:
        1. _mode_lock (for operation mode)
        2. _status_lock (for safety status)
        3. _signal_lock (for signal timing)
        Any code acquiring multiple locks must follow this order.

    Attributes:
        status: Current SafetyStatus
        mode: Current operation mode

    Example:
        >>> monitor = SafetyMonitor(
        ...     get_battery_voltage=lambda: tb.GetBatteryReading(),
        ...     get_fault_status=lambda: tb.GetDriveFault(),
        ...     on_safety_issue=emergency_stop.trigger
        ... )
        >>> monitor.start()
        >>> monitor.set_mode(OperationMode.AUTONOMOUS)
        >>> # During shutdown:
        >>> monitor.terminate()
        >>> monitor.join()
    """

    # Monitor frequency
    POLL_INTERVAL = 0.1  # 10Hz

    def __init__(
        self,
        get_battery_voltage: Optional[Callable[[], float]] = None,
        get_fault_status: Optional[Callable[[], bool]] = None,
        on_safety_issue: Optional[Callable[[str, str], None]] = None,
        battery_stop_voltage: float = 10.5,
        battery_warning_voltage: float = 11.0,
    ):
        """Initialize the safety monitor.

        Args:
            get_battery_voltage: Callback to read battery voltage
            get_fault_status: Callback to check for motor faults
            on_safety_issue: Callback when safety issue detected (trigger, reason)
            battery_stop_voltage: Voltage threshold for automatic stop
            battery_warning_voltage: Voltage threshold for warning
        """
        # Non-daemon thread to ensure clean shutdown
        # Main program must call terminate() + join() on shutdown
        super().__init__(name="SafetyMonitor", daemon=False)

        self._get_battery_voltage = get_battery_voltage
        self._get_fault_status = get_fault_status
        self._on_safety_issue = on_safety_issue
        self._battery_stop_voltage = battery_stop_voltage
        self._battery_warning_voltage = battery_warning_voltage

        self._mode = OperationMode.STOPPED
        # Lock acquisition order: _mode_lock -> _status_lock -> _signal_lock
        # Always acquire locks in this order to prevent deadlocks
        self._mode_lock = threading.Lock()
        self._terminated = threading.Event()
        self._signal_lock = threading.Lock()  # Protects _last_signal_time
        self._last_signal_time = time.time()
        self._signal_timeout = 1.0  # 1 second timeout

        self._status = SafetyStatus(
            mode=OperationMode.STOPPED,
            battery_voltage=0.0,
            battery_ok=True,
            fault_detected=False,
            fault_message="",
            signal_ok=True,
            last_check=0.0,
        )
        self._status_lock = threading.Lock()

    @property
    def status(self) -> SafetyStatus:
        """Get current safety status (thread-safe copy)."""
        with self._status_lock:
            return SafetyStatus(
                mode=self._status.mode,
                battery_voltage=self._status.battery_voltage,
                battery_ok=self._status.battery_ok,
                fault_detected=self._status.fault_detected,
                fault_message=self._status.fault_message,
                signal_ok=self._status.signal_ok,
                last_check=self._status.last_check,
            )

    @property
    def mode(self) -> OperationMode:
        """Get current operation mode."""
        with self._mode_lock:
            return self._mode

    def set_mode(self, mode: OperationMode) -> None:
        """Set operation mode.

        Note: Acquires _mode_lock then _status_lock (following lock order).

        Args:
            mode: New operation mode
        """
        # Lock order: _mode_lock -> _status_lock (as documented in class)
        with self._mode_lock:
            self._mode = mode
        with self._status_lock:
            self._status.mode = mode

    def signal_received(self) -> None:
        """Call this when a valid control signal is received.

        Updates the last signal time to prevent signal loss detection.
        Thread-safe via _signal_lock.
        """
        with self._signal_lock:
            self._last_signal_time = time.time()

    def terminate(self) -> None:
        """Signal the monitor thread to terminate."""
        self._terminated.set()

    def run(self) -> None:
        """Main monitoring loop - runs at 10Hz."""
        print("Safety monitor started (10Hz)")

        while not self._terminated.is_set():
            try:
                self._check_safety()
            except Exception as e:
                # Log but don't crash the safety monitor
                print(f"Safety monitor error: {e}")

            # Wait for next poll interval
            self._terminated.wait(self.POLL_INTERVAL)

        print("Safety monitor terminated")

    def _check_safety(self) -> None:
        """Perform safety checks based on current mode."""
        now = time.time()
        issues = []

        with self._mode_lock:
            current_mode = self._mode

        # Check signal timing (thread-safe read)
        with self._signal_lock:
            last_signal = self._last_signal_time
        signal_ok = (now - last_signal) < self._signal_timeout

        # Read battery voltage if available
        battery_voltage = 0.0
        battery_ok = True
        if self._get_battery_voltage:
            try:
                battery_voltage = self._get_battery_voltage()
            except Exception as e:
                _logger.error(
                    "Failed to read battery voltage: %s", e, exc_info=True
                )
                battery_voltage = 0.0

        # Read fault status if available
        fault_detected = False
        fault_message = ""
        if self._get_fault_status:
            try:
                fault_detected = self._get_fault_status()
                if fault_detected:
                    fault_message = "Motor driver fault detected"
            except Exception as e:
                _logger.error(
                    "Failed to read fault status: %s", e, exc_info=True
                )
                fault_detected = False
                fault_message = ""

        # Mode-dependent checks
        if current_mode == OperationMode.AUTONOMOUS:
            # Autonomous: strict battery check
            if battery_voltage > 0 and battery_voltage < self._battery_stop_voltage:
                battery_ok = False
                issues.append(f"Battery critical: {battery_voltage:.1f}V")

            if fault_detected:
                issues.append(fault_message)

            if not signal_ok:
                issues.append("Signal lost")

        elif current_mode == OperationMode.MANUAL:
            # Manual: only signal loss triggers stop
            # Battery warning is advisory only
            if battery_voltage > 0 and battery_voltage < self._battery_warning_voltage:
                # Warning only, don't stop
                pass

            if not signal_ok:
                issues.append("Signal lost")

        # Update status
        with self._status_lock:
            self._status.battery_voltage = battery_voltage
            self._status.battery_ok = battery_ok
            self._status.fault_detected = fault_detected
            self._status.fault_message = fault_message
            self._status.signal_ok = signal_ok
            self._status.last_check = now

        # Trigger safety callback if issues found
        if issues and self._on_safety_issue and current_mode != OperationMode.STOPPED:
            reason = "; ".join(issues)
            self._on_safety_issue("SafetyMonitor", reason)
