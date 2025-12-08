# coding: utf-8
"""Emergency Stop implementation for MonsterBorg (ADR-009).

This module provides lock-free emergency stop accessible to ANY user.
Target response time: <100ms

The emergency stop:
- Immediately sets motor power to zero
- Is lock-free for guaranteed response time
- Can be triggered by any connected user (not just controller)
- Logs all emergency stop events

See Also:
    - docs/DECISIONS.md: ADR-009 for safety system architecture
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

# Module logger for emergency stop events
_logger = logging.getLogger(__name__)


@dataclass
class EmergencyStopEvent:
    """Record of an emergency stop event."""

    timestamp: float
    triggered_by: str
    reason: str


class EmergencyStop:
    """Lock-free emergency stop implementation.

    Uses atomic operations where possible to minimize latency.
    ANY user can trigger emergency stop - this is intentional for safety.

    Attributes:
        is_stopped: Current emergency stop state (atomic read)
        history: List of recent emergency stop events

    Example:
        >>> estop = EmergencyStop(motor_stop_callback=motors_off)
        >>> estop.trigger("user1", "Manual stop requested")
        >>> estop.is_stopped
        True
        >>> estop.reset("admin")
        True
    """

    # Maximum events to keep in history
    MAX_HISTORY = 100

    def __init__(
        self,
        motor_stop_callback: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[bool, str], None]] = None,
    ):
        """Initialize the emergency stop system.

        Args:
            motor_stop_callback: Function to call to stop motors (must be fast!)
            on_state_change: Callback when stop state changes (is_stopped, reason)
        """
        # Use threading.Event for atomic state - it's lock-free for is_set()
        self._stopped = threading.Event()
        self._motor_stop = motor_stop_callback
        self._on_state_change = on_state_change
        self._history: List[EmergencyStopEvent] = []
        self._history_lock = threading.Lock()

    @property
    def is_stopped(self) -> bool:
        """Check if emergency stop is active (lock-free read)."""
        return self._stopped.is_set()

    def trigger(self, triggered_by: str = "system", reason: str = "Emergency stop") -> None:
        """Trigger emergency stop - accessible to ANY user.

        This method is designed to be as fast as possible.
        It uses atomic operations and defers logging to avoid blocking.

        Args:
            triggered_by: User or system that triggered the stop
            reason: Human-readable reason for the stop
        """
        # Set stop flag first (atomic)
        already_stopped = self._stopped.is_set()
        self._stopped.set()

        # Stop motors immediately
        if self._motor_stop and not already_stopped:
            try:
                self._motor_stop()
            except Exception:
                # Log but don't fail - safety critical path must complete
                _logger.exception("Motor stop callback failed")

        # Log event (non-blocking if possible)
        event = EmergencyStopEvent(
            timestamp=time.time(),
            triggered_by=triggered_by,
            reason=reason,
        )

        # Try to log without blocking
        if self._history_lock.acquire(blocking=False):
            try:
                self._history.append(event)
                # Trim history if needed
                if len(self._history) > self.MAX_HISTORY:
                    self._history = self._history[-self.MAX_HISTORY :]
            finally:
                self._history_lock.release()

        # Notify state change
        if self._on_state_change and not already_stopped:
            try:
                self._on_state_change(True, reason)
            except Exception:
                _logger.exception("State change callback failed during trigger")

    def reset(self, reset_by: str = "system") -> bool:
        """Reset emergency stop state.

        Args:
            reset_by: User or system resetting the stop

        Returns:
            True if reset successful, False if was not stopped
        """
        if not self._stopped.is_set():
            return False

        self._stopped.clear()

        # Log the reset
        event = EmergencyStopEvent(
            timestamp=time.time(),
            triggered_by=reset_by,
            reason="Emergency stop reset",
        )
        with self._history_lock:
            self._history.append(event)
            # Trim history if needed
            if len(self._history) > self.MAX_HISTORY:
                self._history = self._history[-self.MAX_HISTORY :]

        if self._on_state_change:
            try:
                self._on_state_change(False, "Reset by " + reset_by)
            except Exception:
                _logger.exception("State change callback failed during reset")

        return True

    def get_history(self, limit: int = 10) -> List[EmergencyStopEvent]:
        """Get recent emergency stop events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent EmergencyStopEvent objects
        """
        with self._history_lock:
            return self._history[-limit:]

    def wait_for_reset(self, timeout: Optional[float] = None) -> bool:
        """Wait for emergency stop to be reset.

        Args:
            timeout: Maximum seconds to wait (None = wait forever, 0 = non-blocking)

        Returns:
            True if reset occurred (or not stopped), False if timeout or still stopped
        """
        # If not stopped, return immediately
        if not self._stopped.is_set():
            return True

        # Handle timeout==0 as immediate non-blocking check
        if timeout == 0:
            return not self._stopped.is_set()

        # We need to wait for the flag to be cleared
        # threading.Event doesn't have wait_for_clear, so we poll
        start = time.time()
        while self._stopped.is_set():
            if timeout is not None and (time.time() - start) > timeout:
                return False
            time.sleep(0.01)  # 10ms poll interval
        return True
