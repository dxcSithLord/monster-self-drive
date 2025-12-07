#!/usr/bin/env python
# coding: utf-8
"""Tests for safety module."""

import threading
import time

import pytest

from src.safety.control_manager import ControlManager, UserRole
from src.safety.emergency_stop import EmergencyStop


class TestEmergencyStop:
    """Tests for EmergencyStop class."""

    def test_initial_state(self) -> None:
        """Test that emergency stop is not active initially."""
        estop = EmergencyStop()
        assert estop.is_stopped is False

    def test_trigger_sets_stopped(self) -> None:
        """Test that triggering sets stopped state."""
        estop = EmergencyStop()
        estop.trigger("test_user", "Test trigger")
        assert estop.is_stopped is True

    def test_trigger_calls_callback(self) -> None:
        """Test that triggering calls motor stop callback."""
        callback_called = threading.Event()

        def motor_stop() -> None:
            callback_called.set()

        estop = EmergencyStop(motor_stop_callback=motor_stop)
        estop.trigger()
        assert callback_called.is_set()

    def test_reset_clears_stopped(self) -> None:
        """Test that reset clears stopped state."""
        estop = EmergencyStop()
        estop.trigger()
        assert estop.is_stopped is True
        result = estop.reset("admin")
        assert result is True
        assert estop.is_stopped is False

    def test_reset_when_not_stopped(self) -> None:
        """Test that reset returns False when not stopped."""
        estop = EmergencyStop()
        result = estop.reset()
        assert result is False

    def test_history_recording(self) -> None:
        """Test that events are recorded in history."""
        estop = EmergencyStop()
        estop.trigger("user1", "First stop")
        estop.reset("admin")
        estop.trigger("user2", "Second stop")

        history = estop.get_history()
        assert len(history) == 3
        assert history[0].triggered_by == "user1"
        assert history[0].reason == "First stop"

    def test_any_user_can_trigger(self) -> None:
        """Test that any user can trigger emergency stop (safety feature)."""
        estop = EmergencyStop()

        # Simulate multiple users triggering
        for user in ["controller", "observer1", "observer2", "random_user"]:
            estop.reset("admin")
            estop.trigger(user, f"Stop by {user}")
            assert estop.is_stopped is True


class TestControlManager:
    """Tests for ControlManager class."""

    def test_first_user_gets_control(self) -> None:
        """Test that first user requesting control gets it."""
        manager = ControlManager()
        result = manager.request_control("user1")
        assert result is True
        assert manager.active_controller == "user1"

    def test_second_user_becomes_observer(self) -> None:
        """Test that second user becomes observer."""
        manager = ControlManager()
        manager.request_control("user1")
        result = manager.request_control("user2")
        assert result is False
        assert manager.get_user_role("user2") == UserRole.OBSERVER
        assert manager.observer_count == 1

    def test_controller_disconnect_promotes_observer(self) -> None:
        """Test that when controller disconnects, observer is promoted."""
        manager = ControlManager()
        manager.request_control("user1")
        manager.request_control("user2")

        manager.disconnect("user1")

        assert manager.active_controller == "user2"
        assert manager.get_user_role("user2") == UserRole.CONTROLLER

    def test_takeover_request(self) -> None:
        """Test takeover request flow."""
        manager = ControlManager()
        manager.request_control("user1")
        manager.request_control("user2")

        # User2 requests takeover
        result = manager.request_takeover("user2")
        assert result is True

        # User1 approves
        result = manager.approve_takeover("user1")
        assert result is True
        assert manager.active_controller == "user2"

    def test_controller_cannot_request_takeover(self) -> None:
        """Test that current controller cannot request takeover."""
        manager = ControlManager()
        manager.request_control("user1")
        result = manager.request_takeover("user1")
        assert result is False
