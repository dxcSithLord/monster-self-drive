# coding: utf-8
"""Control Manager for single-user control model (ADR-004).

This module implements the single active user model:
- One user has control at a time, others are observers
- Second user can request takeover or auto-gains when first disconnects
- ANY user can trigger emergency stop

See Also:
    - docs/DECISIONS.md: ADR-004 for multi-user control model decision
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

# Module logger
_logger = logging.getLogger(__name__)


class UserRole(Enum):
    """Role of a connected user."""

    CONTROLLER = "controller"
    OBSERVER = "observer"
    DISCONNECTED = "disconnected"


@dataclass
class UserSession:
    """Represents a connected user session."""

    user_id: str
    role: UserRole
    connected_at: float
    last_activity: float


class ControlManager:
    """Manages single-user control with observer mode for additional users.

    Thread-safe implementation for managing control handoff between users.
    Implements ADR-004 single active user model.

    Attributes:
        active_controller: Current user with control (None if no controller)
        observers: Set of user IDs in observer mode
        takeover_requested: User ID requesting takeover (if any)

    Example:
        >>> manager = ControlManager()
        >>> manager.request_control("user1")
        True
        >>> manager.request_control("user2")
        False  # user2 becomes observer
        >>> manager.request_takeover("user2")
        True  # takeover request registered
    """

    def __init__(
        self,
        on_control_change: Optional[Callable[[str, UserRole], None]] = None,
        takeover_timeout: float = 10.0,
    ):
        """Initialize the control manager.

        Args:
            on_control_change: Callback when control changes (user_id, new_role)
            takeover_timeout: Seconds to wait for takeover confirmation before
                auto-granting. Note: Auto-takeover is not yet implemented;
                this parameter is stored for future use.
        """
        self._lock = threading.RLock()
        self._sessions: dict[str, UserSession] = {}
        self._active_controller: Optional[str] = None
        self._takeover_requester: Optional[str] = None
        # TODO: Implement auto-takeover timer that grants control after timeout
        # if controller doesn't respond to takeover request
        self._takeover_timeout = takeover_timeout
        self._on_control_change = on_control_change

    @property
    def active_controller(self) -> Optional[str]:
        """Get the current controller's user ID."""
        with self._lock:
            return self._active_controller

    @property
    def observer_count(self) -> int:
        """Get the number of observers."""
        with self._lock:
            return sum(
                1
                for s in self._sessions.values()
                if s.role == UserRole.OBSERVER
            )

    def request_control(self, user_id: str) -> bool:
        """Request control of the robot.

        Args:
            user_id: Unique identifier for the requesting user

        Returns:
            True if control was granted, False if user becomes observer
        """
        with self._lock:
            now = time.time()

            if user_id in self._sessions:
                # Update existing session
                self._sessions[user_id].last_activity = now
                if self._sessions[user_id].role == UserRole.CONTROLLER:
                    return True
            else:
                # New session
                self._sessions[user_id] = UserSession(
                    user_id=user_id,
                    role=UserRole.DISCONNECTED,
                    connected_at=now,
                    last_activity=now,
                )

            if self._active_controller is None:
                # No active controller - grant control
                self._active_controller = user_id
                self._sessions[user_id].role = UserRole.CONTROLLER
                self._notify_change(user_id, UserRole.CONTROLLER)
                return True
            else:
                # Controller exists - become observer
                self._sessions[user_id].role = UserRole.OBSERVER
                self._notify_change(user_id, UserRole.OBSERVER)
                return False

    def request_takeover(self, user_id: str) -> bool:
        """Request to take over control from current controller.

        The current controller will be notified and can approve/deny.
        If controller doesn't respond within timeout, takeover is granted.

        Only one takeover request can be pending at a time. If a request
        is already pending, new requests are rejected until the current
        one is approved, denied, or the requester disconnects.

        Args:
            user_id: User ID requesting takeover

        Returns:
            True if takeover request registered, False if already controller,
            not connected, or another takeover request is pending
        """
        with self._lock:
            if user_id == self._active_controller:
                return False  # Already controller

            if user_id not in self._sessions:
                return False  # Not connected

            # Reject if another takeover request is already pending
            if self._takeover_requester is not None:
                return False  # Takeover already pending

            self._takeover_requester = user_id
            # TODO: Implement takeover notification to current controller
            # TODO: Implement timeout for auto-takeover
            return True

    def cancel_takeover(self, user_id: str) -> bool:
        """Cancel a pending takeover request.

        Can be called by the requester to cancel their own request,
        or by the controller to deny the request.

        Args:
            user_id: User ID canceling (must be requester or controller)

        Returns:
            True if takeover was canceled, False if no pending request
            or user not authorized to cancel
        """
        with self._lock:
            if self._takeover_requester is None:
                return False

            # Either the requester or controller can cancel
            if user_id != self._takeover_requester and user_id != self._active_controller:
                return False

            self._takeover_requester = None
            return True

    def has_pending_takeover(self) -> bool:
        """Check if there's a pending takeover request.

        Returns:
            True if a takeover request is pending
        """
        with self._lock:
            return self._takeover_requester is not None

    def approve_takeover(self, approver_id: str) -> bool:
        """Approve a pending takeover request.

        Args:
            approver_id: Must be the current controller

        Returns:
            True if takeover approved and completed, False if approver is not
            controller, no pending request, or requester has disconnected
        """
        with self._lock:
            if approver_id != self._active_controller:
                return False

            if self._takeover_requester is None:
                return False

            new_controller = self._takeover_requester

            # Check if the requester is still connected
            if new_controller not in self._sessions:
                # Requester disconnected while waiting - clear the request
                self._takeover_requester = None
                return False

            old_controller = self._active_controller

            # Transfer control
            self._active_controller = new_controller
            self._sessions[new_controller].role = UserRole.CONTROLLER
            self._sessions[old_controller].role = UserRole.OBSERVER
            self._takeover_requester = None

            self._notify_change(new_controller, UserRole.CONTROLLER)
            self._notify_change(old_controller, UserRole.OBSERVER)
            return True

    def disconnect(self, user_id: str) -> None:
        """Handle user disconnection.

        If controller disconnects, control passes to first observer.
        If the disconnecting user had a pending takeover request, it is cleared.
        Notifies via callback when users disconnect for lifecycle tracking.

        Args:
            user_id: Disconnecting user's ID
        """
        with self._lock:
            if user_id not in self._sessions:
                return

            # Clear pending takeover request if the requester is disconnecting
            if self._takeover_requester == user_id:
                self._takeover_requester = None

            was_controller = user_id == self._active_controller
            self._sessions[user_id].role = UserRole.DISCONNECTED
            del self._sessions[user_id]

            # Notify that user disconnected (for lifecycle tracking symmetry)
            self._notify_change(user_id, UserRole.DISCONNECTED)

            if was_controller:
                self._active_controller = None
                # Find first observer to promote
                for session in self._sessions.values():
                    if session.role == UserRole.OBSERVER:
                        self._active_controller = session.user_id
                        session.role = UserRole.CONTROLLER
                        self._notify_change(session.user_id, UserRole.CONTROLLER)
                        break

    def update_activity(self, user_id: str) -> None:
        """Update last activity timestamp for a user.

        Args:
            user_id: User ID to update
        """
        with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id].last_activity = time.time()

    def get_user_role(self, user_id: str) -> UserRole:
        """Get the role of a user.

        Args:
            user_id: User ID to query

        Returns:
            UserRole enum value
        """
        with self._lock:
            if user_id in self._sessions:
                return self._sessions[user_id].role
            return UserRole.DISCONNECTED

    def _notify_change(self, user_id: str, new_role: UserRole) -> None:
        """Notify callback of control change."""
        if self._on_control_change:
            try:
                self._on_control_change(user_id, new_role)
            except Exception as e:
                # Log but don't let callback errors affect control manager
                _logger.error(
                    "Error in control change callback for user %s -> %s: %s",
                    user_id,
                    new_role.value,
                    e,
                    exc_info=True,
                )
