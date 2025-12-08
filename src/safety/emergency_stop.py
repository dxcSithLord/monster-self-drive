# coding: utf-8
"""Emergency Stop implementation for MonsterBorg (ADR-009).

This module provides emergency stop accessible to ANY user.
Target response time: <100ms

The emergency stop:
- Immediately sets motor power to zero
- Uses minimal locking for state transitions while keeping reads lock-free
- Can be triggered by any connected user (not just controller)
- Logs all emergency stop events

Thread Safety:
    - is_stopped property: Lock-free read (threading.Event.is_set())
    - trigger(): Uses _state_lock for atomic test-and-set + motor stop
    - reset(): Uses _state_lock for atomic transition
    - Callbacks invoked outside lock to prevent deadlocks

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
    """Emergency stop implementation with thread-safe state transitions.

    Uses a state lock for atomic transitions while keeping reads lock-free.
    ANY user can trigger emergency stop - this is intentional for safety.

    Thread Safety:
        - is_stopped: Lock-free read via threading.Event.is_set()
        - trigger()/reset(): Protected by _state_lock for atomic transitions
        - Motor stop callback called exactly once per trigger (not per caller)
        - State change callback called exactly once per transition

    Attributes:
        is_stopped: Current emergency stop state (lock-free read)
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
        # Use threading.Event for state - is_set() is lock-free for reads
        self._stopped = threading.Event()
        self._motor_stop = motor_stop_callback
        self._on_state_change = on_state_change
        self._history: List[EmergencyStopEvent] = []
        self._history_lock = threading.Lock()
        # State lock for atomic test-and-set/clear transitions
        # Ensures motor_stop and on_state_change are called exactly once per transition
        self._state_lock = threading.Lock()

    @property
    def is_stopped(self) -> bool:
        """Check if emergency stop is active (lock-free read)."""
        return self._stopped.is_set()

    def trigger(self, triggered_by: str = "system", reason: str = "Emergency stop") -> None:
        """Trigger emergency stop - accessible to ANY user.

        Thread-safe: Uses _state_lock for atomic test-and-set to ensure
        motor_stop callback is called exactly once per stop event.

        Args:
            triggered_by: User or system that triggered the stop
            reason: Human-readable reason for the stop
        """
        # Atomic test-and-set with motor stop under lock
        # This ensures only one thread calls motor_stop per transition
        performed_transition = False
        motor_callback = None
        state_callback = None
        callback_reason = reason

        with self._state_lock:
            if not self._stopped.is_set():
                self._stopped.set()
                performed_transition = True
                # Capture callbacks to invoke outside lock
                motor_callback = self._motor_stop
                state_callback = self._on_state_change
            else:
                # Already stopped, just set again (idempotent)
                self._stopped.set()

        # Call motor stop outside lock (but only if we performed the transition)
        if motor_callback and performed_transition:
            try:
                motor_callback()
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

        # Notify state change outside lock (only if we performed the transition)
        if state_callback and performed_transition:
            try:
                state_callback(True, callback_reason)
            except Exception:
                _logger.exception("State change callback failed during trigger")

    def reset(self, reset_by: str = "system") -> bool:
        """Reset emergency stop state.

        Thread-safe: Uses _state_lock for atomic check-and-clear to ensure
        on_state_change callback is called exactly once per reset.

        Args:
            reset_by: User or system resetting the stop

        Returns:
            True if reset successful, False if was not stopped
        """
        # Atomic check-and-clear under lock
        # This ensures only one thread performs the reset transition
        performed_transition = False
        state_callback = None
        callback_message = f"Reset by {reset_by}"

        with self._state_lock:
            if self._stopped.is_set():
                self._stopped.clear()
                performed_transition = True
                state_callback = self._on_state_change

        if not performed_transition:
            return False

        # Log the reset (outside state lock, but uses history lock)
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

        # Notify state change outside lock (only if we performed the transition)
        if state_callback:
            try:
                state_callback(False, callback_message)
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
