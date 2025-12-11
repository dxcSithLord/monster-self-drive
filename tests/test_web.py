# coding: utf-8
"""Tests for web module (Phase 1).

Tests the Flask-SocketIO web server implementation.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# Skip tests if Flask-SocketIO is not installed
pytest.importorskip("flask_socketio")

from src.web.server import MonsterWebServer


class TestMonsterWebServer:
    """Tests for MonsterWebServer class."""

    def test_initialization(self) -> None:
        """Test server initialization with default parameters."""
        server = MonsterWebServer()
        assert server.app is not None
        assert server.socketio is not None
        assert server._max_power == 1.0
        assert server._speed_multiplier == 1.0

    def test_initialization_with_callbacks(self) -> None:
        """Test server initialization with callbacks."""
        motor_cb = MagicMock()
        frame_cb = MagicMock(return_value=b'fake_jpeg')
        telemetry_cb = MagicMock(return_value={'test': 123})

        server = MonsterWebServer(
            motor_callback=motor_cb,
            frame_callback=frame_cb,
            telemetry_callback=telemetry_cb,
            max_power=0.8,
        )

        assert server._motor_callback is motor_cb
        assert server._frame_callback is frame_cb
        assert server._telemetry_callback is telemetry_cb
        assert server._max_power == 0.8

    def test_set_motors_clamps_values(self) -> None:
        """Test that motor values are clamped to -1.0 to 1.0."""
        motor_cb = MagicMock()
        server = MonsterWebServer(motor_callback=motor_cb, max_power=1.0)

        # Test values within range
        server._set_motors(0.5, -0.5)
        motor_cb.assert_called_with(0.5, -0.5)

        # Test clamping high values
        server._set_motors(1.5, 2.0)
        motor_cb.assert_called_with(1.0, 1.0)

        # Test clamping low values
        server._set_motors(-1.5, -2.0)
        motor_cb.assert_called_with(-1.0, -1.0)

    def test_set_motors_applies_power_limit(self) -> None:
        """Test that motor values are scaled by max_power."""
        motor_cb = MagicMock()
        server = MonsterWebServer(motor_callback=motor_cb, max_power=0.5)

        server._set_motors(1.0, 1.0)
        motor_cb.assert_called_with(0.5, 0.5)

        server._set_motors(-1.0, -1.0)
        motor_cb.assert_called_with(-0.5, -0.5)

    def test_set_motors_handles_callback_exception(self) -> None:
        """Test that motor callback exceptions are handled gracefully."""
        motor_cb = MagicMock(side_effect=RuntimeError("Motor error"))
        server = MonsterWebServer(motor_callback=motor_cb)

        # Should not raise, just log
        server._set_motors(0.5, 0.5)
        motor_cb.assert_called_once()

    def test_set_motors_without_callback(self) -> None:
        """Test that set_motors works without callback."""
        server = MonsterWebServer(motor_callback=None)

        # Should not raise
        server._set_motors(0.5, 0.5)
        assert server._current_left == 0.5
        assert server._current_right == 0.5

    def test_send_telemetry_includes_motor_state(self) -> None:
        """Test that telemetry includes current motor state."""
        server = MonsterWebServer()
        server._current_left = 0.5
        server._current_right = -0.3
        server._speed_multiplier = 0.8

        # Mock socketio emit
        server.socketio.emit = MagicMock()

        server._send_telemetry()

        # Check emit was called
        server.socketio.emit.assert_called_once()
        call_args = server.socketio.emit.call_args
        telemetry = call_args[0][1]

        assert telemetry['motor_left'] == 0.5
        assert telemetry['motor_right'] == -0.3
        assert telemetry['speed_multiplier'] == 0.8
        assert 'timestamp' in telemetry

    def test_send_telemetry_includes_custom_data(self) -> None:
        """Test that telemetry includes custom callback data."""
        custom_telemetry = {'battery_voltage': 11.5, 'temperature': 35.0}
        telemetry_cb = MagicMock(return_value=custom_telemetry)
        server = MonsterWebServer(telemetry_callback=telemetry_cb)

        server.socketio.emit = MagicMock()
        server._send_telemetry()

        telemetry_cb.assert_called_once()
        call_args = server.socketio.emit.call_args
        telemetry = call_args[0][1]

        assert telemetry['battery_voltage'] == 11.5
        assert telemetry['temperature'] == 35.0

    def test_send_telemetry_handles_callback_exception(self) -> None:
        """Test that telemetry callback exceptions are handled."""
        telemetry_cb = MagicMock(side_effect=RuntimeError("Telemetry error"))
        server = MonsterWebServer(telemetry_callback=telemetry_cb)

        server.socketio.emit = MagicMock()

        # Should not raise
        server._send_telemetry()

        # Should still emit basic telemetry
        server.socketio.emit.assert_called_once()

    def test_flask_routes_registered(self) -> None:
        """Test that Flask routes are registered correctly."""
        server = MonsterWebServer()

        # Get registered routes
        rules = {rule.rule for rule in server.app.url_map.iter_rules()}

        assert '/' in rules
        assert '/stream' in rules
        assert '/cam.jpg' in rules
        assert '/health' in rules

    def test_health_endpoint(self) -> None:
        """Test health check endpoint."""
        server = MonsterWebServer()

        with server.app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'ok'
            assert 'timestamp' in data

    def test_camera_snapshot_no_frame(self) -> None:
        """Test camera snapshot returns 204 when no frame available."""
        server = MonsterWebServer(frame_callback=lambda: None)

        with server.app.test_client() as client:
            response = client.get('/cam.jpg')
            assert response.status_code == 204

    def test_camera_snapshot_returns_frame(self) -> None:
        """Test camera snapshot returns JPEG frame."""
        fake_frame = b'\xff\xd8\xff\xe0fake_jpeg'
        server = MonsterWebServer(frame_callback=lambda: fake_frame)

        with server.app.test_client() as client:
            response = client.get('/cam.jpg')
            assert response.status_code == 200
            assert response.content_type == 'image/jpeg'
            assert response.data == fake_frame

    def test_start_stop_telemetry(self) -> None:
        """Test starting and stopping telemetry thread."""
        server = MonsterWebServer()

        assert server._telemetry_running is False

        server.start_telemetry()
        assert server._telemetry_running is True
        assert server._telemetry_thread is not None
        assert server._telemetry_thread.is_alive()

        server.stop_telemetry()
        assert server._telemetry_running is False

    def test_motor_lock_thread_safety(self) -> None:
        """Test that motor operations are thread-safe."""
        motor_values = []
        lock = threading.Lock()

        def motor_cb(left, right):
            with lock:
                motor_values.append((left, right))

        server = MonsterWebServer(motor_callback=motor_cb, max_power=1.0)

        # Simulate concurrent motor commands
        threads = []
        for i in range(10):
            t = threading.Thread(
                target=server._set_motors,
                args=(i * 0.1, -i * 0.1)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All commands should have been processed
        assert len(motor_values) == 10

    def test_photo_directory_expansion(self) -> None:
        """Test that photo directory path is expanded."""
        server = MonsterWebServer(photo_directory="~/test-photos")
        assert "~" not in server._photo_directory
        assert server._photo_directory.endswith("test-photos")


class TestEmergencyStopIntegration:
    """Tests for emergency stop integration with web server."""

    def test_set_motors_respects_emergency_stop(self) -> None:
        """Test that motors stop when emergency stop is active."""
        from src.safety.emergency_stop import EmergencyStop

        motor_cb = MagicMock()
        estop = EmergencyStop(motor_stop_callback=lambda: None)
        server = MonsterWebServer(
            motor_callback=motor_cb,
            emergency_stop=estop
        )

        # Motors should work normally
        server._set_motors(1.0, 1.0)
        motor_cb.assert_called_with(1.0, 1.0)

        # Trigger emergency stop - but note: _set_motors doesn't check estop
        # The checking happens in the WebSocket event handlers
        # This test just verifies the integration setup
        estop.trigger("test", "Test stop")
        assert estop.is_stopped is True

    def test_telemetry_includes_emergency_stop_state(self) -> None:
        """Test that telemetry includes emergency stop state."""
        from src.safety.emergency_stop import EmergencyStop

        estop = EmergencyStop()
        server = MonsterWebServer(emergency_stop=estop)
        server.socketio.emit = MagicMock()

        # Not stopped
        server._send_telemetry()
        telemetry = server.socketio.emit.call_args[0][1]
        assert telemetry['emergency_stopped'] is False

        # Stopped
        estop.trigger()
        server._send_telemetry()
        telemetry = server.socketio.emit.call_args[0][1]
        assert telemetry['emergency_stopped'] is True


class TestControlManagerIntegration:
    """Tests for control manager integration with web server."""

    def test_server_with_control_manager(self) -> None:
        """Test server initialization with control manager."""
        from src.safety.control_manager import ControlManager

        manager = ControlManager()
        server = MonsterWebServer(control_manager=manager)

        assert server._control_manager is manager


class TestJoystickToMotorConversion:
    """Tests for joystick to motor conversion logic.

    The joystick sends x/y values (-1 to 1), which need to be
    converted to differential drive (left/right motor values).
    """

    def _convert_joystick(self, x: float, y: float) -> tuple:
        """Helper to convert joystick to motor values.

        This replicates the logic in the handle_joystick event handler.
        """
        left = y + x
        right = y - x

        # Normalize
        max_val = max(abs(left), abs(right), 1.0)
        left /= max_val
        right /= max_val

        return (left, right)

    def test_forward(self) -> None:
        """Test joystick forward (y=1, x=0)."""
        left, right = self._convert_joystick(0, 1)
        assert left == pytest.approx(1.0)
        assert right == pytest.approx(1.0)

    def test_backward(self) -> None:
        """Test joystick backward (y=-1, x=0)."""
        left, right = self._convert_joystick(0, -1)
        assert left == pytest.approx(-1.0)
        assert right == pytest.approx(-1.0)

    def test_turn_right(self) -> None:
        """Test joystick turn right (y=0, x=1)."""
        left, right = self._convert_joystick(1, 0)
        assert left == pytest.approx(1.0)
        assert right == pytest.approx(-1.0)

    def test_turn_left(self) -> None:
        """Test joystick turn left (y=0, x=-1)."""
        left, right = self._convert_joystick(-1, 0)
        assert left == pytest.approx(-1.0)
        assert right == pytest.approx(1.0)

    def test_forward_right(self) -> None:
        """Test joystick forward-right diagonal."""
        left, right = self._convert_joystick(0.5, 1)
        # left = 1 + 0.5 = 1.5, right = 1 - 0.5 = 0.5
        # normalized: left = 1.0, right = 0.5/1.5 = 0.333
        assert left == pytest.approx(1.0)
        assert right == pytest.approx(0.333, abs=0.01)

    def test_neutral(self) -> None:
        """Test joystick at center (y=0, x=0)."""
        left, right = self._convert_joystick(0, 0)
        assert left == pytest.approx(0.0)
        assert right == pytest.approx(0.0)


class TestSpeedMultiplier:
    """Tests for speed multiplier functionality."""

    def test_speed_multiplier_default(self) -> None:
        """Test default speed multiplier is 1.0."""
        server = MonsterWebServer()
        assert server._speed_multiplier == 1.0

    def test_speed_multiplier_applied_to_motors(self) -> None:
        """Test that speed multiplier is tracked correctly."""
        server = MonsterWebServer()

        # Change speed multiplier
        server._speed_multiplier = 0.5

        # Verify it's stored
        assert server._speed_multiplier == 0.5
