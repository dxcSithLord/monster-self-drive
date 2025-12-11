# coding: utf-8
"""Flask-SocketIO web server for MonsterBorg (ADR-001).

This module implements the mobile-optimized web interface with:
- Flask-SocketIO for real-time WebSocket communication
- Responsive design for mobile devices
- Touch controls with continuous movement
- Single-user control model (ADR-004)
- Emergency stop accessible to any user (ADR-009)

See Also:
    - docs/DECISIONS.md: ADR-001 for WebSocket library decision
    - docs/DECISIONS.md: ADR-004 for multi-user control model
    - docs/IMPLEMENTATION_PLAN.md: Phase 1 specification
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from flask import Flask, Response, render_template, request
from flask_socketio import SocketIO, emit

# Module logger
_logger = logging.getLogger(__name__)


class MonsterWebServer:
    """Flask-SocketIO web server for MonsterBorg control.

    Provides:
    - Mobile-optimized web interface
    - Real-time WebSocket communication
    - Touch and joystick controls
    - Telemetry streaming
    - Emergency stop (any user)
    - Single-user control model

    Thread Safety:
        - All motor commands go through command queue
        - Frame buffer protected by lock
        - Emergency stop is lock-free read

    Example:
        >>> server = MonsterWebServer(
        ...     motor_callback=set_motors,
        ...     frame_callback=get_frame,
        ...     telemetry_callback=get_telemetry,
        ...     emergency_stop=estop
        ... )
        >>> server.run(host='127.0.0.1', port=8080)
    """

    def __init__(
        self,
        motor_callback: Optional[Callable[[float, float], None]] = None,
        frame_callback: Optional[Callable[[], Optional[bytes]]] = None,
        telemetry_callback: Optional[Callable[[], Dict[str, Any]]] = None,
        emergency_stop: Optional[Any] = None,
        control_manager: Optional[Any] = None,
        photo_directory: str = "~/monster-photos",
        max_power: float = 1.0,
    ):
        """Initialize the web server.

        Args:
            motor_callback: Function to set motor powers (left, right) in range -1.0 to 1.0
            frame_callback: Function returning current JPEG frame as bytes
            telemetry_callback: Function returning telemetry dict
            emergency_stop: EmergencyStop instance for safety controls
            control_manager: ControlManager instance for multi-user handling
            photo_directory: Directory to save captured photos
            max_power: Maximum motor power limit (0.0 to 1.0)
        """
        self._motor_callback = motor_callback
        self._frame_callback = frame_callback
        self._telemetry_callback = telemetry_callback
        self._emergency_stop = emergency_stop
        self._control_manager = control_manager
        self._photo_directory = os.path.expanduser(photo_directory)
        self._max_power = max_power

        # Current motor state
        self._current_left = 0.0
        self._current_right = 0.0
        self._motor_lock = threading.Lock()

        # Speed multiplier (0.0 to 1.0)
        self._speed_multiplier = 1.0

        # Watchdog tracking
        self._last_command_time: Dict[str, float] = {}
        self._watchdog_timeout = 1.0  # seconds

        # Telemetry streaming
        self._telemetry_interval = 0.1  # 10 Hz
        self._telemetry_running = False
        self._telemetry_thread: Optional[threading.Thread] = None

        # Create Flask app with template folder
        template_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"

        self.app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(static_dir),
        )
        self.app.config['SECRET_KEY'] = os.urandom(24)

        # Create SocketIO with async_mode for threading
        self.socketio = SocketIO(
            self.app,
            async_mode='threading',
            cors_allowed_origins="*",
            ping_timeout=10,
            ping_interval=5,
        )

        # Register routes and events
        self._register_routes()
        self._register_socketio_events()

    def _register_routes(self) -> None:
        """Register HTTP routes."""

        @self.app.route('/')
        def index():
            """Serve the main control page."""
            return render_template('index.html')

        @self.app.route('/stream')
        def stream():
            """Serve the camera stream page (for iframe embedding)."""
            return render_template('stream.html')

        @self.app.route('/cam.jpg')
        def camera_snapshot():
            """Return current camera frame as JPEG."""
            if self._frame_callback:
                frame = self._frame_callback()
                if frame is not None:
                    return Response(frame, mimetype='image/jpeg')
            return Response(b'', status=204)

        @self.app.route('/health')
        def health():
            """Health check endpoint."""
            return {'status': 'ok', 'timestamp': time.time()}

    def _register_socketio_events(self) -> None:
        """Register WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle new WebSocket connection."""
            sid = request.sid
            _logger.info("Client connected: %s", sid)

            # Register with control manager if available
            if self._control_manager:
                granted = self._control_manager.request_control(sid)
                role = 'controller' if granted else 'observer'
                emit('control_status', {
                    'role': role,
                    'message': f"You are {'in control' if granted else 'observing'}",
                })
            else:
                emit('control_status', {'role': 'controller', 'message': 'Connected'})

            # Send initial telemetry
            self._send_telemetry(sid)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle WebSocket disconnection."""
            sid = request.sid
            _logger.info("Client disconnected: %s", sid)

            # Stop motors on disconnect
            self._set_motors(0.0, 0.0)

            # Remove from control manager
            if self._control_manager:
                self._control_manager.disconnect(sid)

            # Clean up watchdog
            if sid in self._last_command_time:
                del self._last_command_time[sid]

        @self.socketio.on('drive')
        def handle_drive(data: Dict[str, Any]):
            """Handle drive command from client.

            Args:
                data: Dict with 'left' and 'right' motor values (-1.0 to 1.0)
            """
            sid = request.sid

            # Check if user has control
            if self._control_manager:
                role = self._control_manager.get_user_role(sid)
                if role.value != 'controller':
                    emit('error', {'message': 'You are not in control'})
                    return

            # Check emergency stop
            if self._emergency_stop and self._emergency_stop.is_stopped:
                emit('error', {'message': 'Emergency stop active'})
                return

            try:
                left = float(data.get('left', 0.0))
                right = float(data.get('right', 0.0))

                # Apply speed multiplier
                left *= self._speed_multiplier
                right *= self._speed_multiplier

                # Set motors
                self._set_motors(left, right)

                # Update watchdog
                self._last_command_time[sid] = time.time()

            except (ValueError, TypeError) as e:
                _logger.warning("Invalid drive command: %s", e)
                emit('error', {'message': 'Invalid drive values'})

        @self.socketio.on('joystick')
        def handle_joystick(data: Dict[str, Any]):
            """Handle joystick input from virtual joystick.

            Args:
                data: Dict with 'x' (-1 to 1) and 'y' (-1 to 1) values
            """
            sid = request.sid

            # Check if user has control
            if self._control_manager:
                role = self._control_manager.get_user_role(sid)
                if role.value != 'controller':
                    return

            # Check emergency stop
            if self._emergency_stop and self._emergency_stop.is_stopped:
                return

            try:
                x = float(data.get('x', 0.0))
                y = float(data.get('y', 0.0))

                # Convert joystick to differential drive
                # y = forward/back, x = left/right
                left = y + x
                right = y - x

                # Normalize to -1.0 to 1.0
                max_val = max(abs(left), abs(right), 1.0)
                left /= max_val
                right /= max_val

                # Apply speed multiplier
                left *= self._speed_multiplier
                right *= self._speed_multiplier

                # Set motors
                self._set_motors(left, right)

                # Update watchdog
                self._last_command_time[sid] = time.time()

            except (ValueError, TypeError) as e:
                _logger.warning("Invalid joystick input: %s", e)

        @self.socketio.on('stop')
        def handle_stop():
            """Handle stop command - stops motors immediately."""
            self._set_motors(0.0, 0.0)

        @self.socketio.on('emergency_stop')
        def handle_emergency_stop(data: Optional[Dict[str, Any]] = None):
            """Handle emergency stop - accessible to ANY user.

            Args:
                data: Optional dict with 'reason' field
            """
            sid = request.sid
            reason = data.get('reason', 'User triggered') if data else 'User triggered'

            _logger.warning("Emergency stop triggered by %s: %s", sid, reason)

            # Trigger emergency stop
            if self._emergency_stop:
                self._emergency_stop.trigger(triggered_by=sid, reason=reason)

            # Also stop motors directly as backup
            self._set_motors(0.0, 0.0)

            # Broadcast to all clients
            self.socketio.emit('emergency_stop_active', {
                'triggered_by': sid,
                'reason': reason,
                'timestamp': time.time(),
            })

        @self.socketio.on('emergency_reset')
        def handle_emergency_reset():
            """Handle emergency stop reset."""
            sid = request.sid

            # Only controller can reset
            if self._control_manager:
                role = self._control_manager.get_user_role(sid)
                if role.value != 'controller':
                    emit('error', {'message': 'Only controller can reset emergency stop'})
                    return

            if self._emergency_stop:
                if self._emergency_stop.reset(reset_by=sid):
                    self.socketio.emit('emergency_stop_cleared', {
                        'reset_by': sid,
                        'timestamp': time.time(),
                    })
                else:
                    emit('error', {'message': 'Emergency stop was not active'})

        @self.socketio.on('set_speed')
        def handle_set_speed(data: Dict[str, Any]):
            """Handle speed multiplier change.

            Args:
                data: Dict with 'speed' value (0.0 to 1.0)
            """
            try:
                speed = float(data.get('speed', 1.0))
                self._speed_multiplier = max(0.0, min(1.0, speed))
                emit('speed_updated', {'speed': self._speed_multiplier})
            except (ValueError, TypeError):
                emit('error', {'message': 'Invalid speed value'})

        @self.socketio.on('request_takeover')
        def handle_request_takeover():
            """Handle request to take over control."""
            sid = request.sid

            if self._control_manager:
                if self._control_manager.request_takeover(sid):
                    # Notify current controller
                    controller = self._control_manager.active_controller
                    if controller:
                        self.socketio.emit(
                            'takeover_requested',
                            {'requester': sid},
                            room=controller
                        )
                    emit('takeover_pending', {'message': 'Takeover request sent'})
                else:
                    emit('error', {'message': 'Cannot request takeover'})

        @self.socketio.on('approve_takeover')
        def handle_approve_takeover():
            """Handle approval of takeover request."""
            sid = request.sid

            if self._control_manager:
                if self._control_manager.approve_takeover(sid):
                    # Notify all clients of control change
                    new_controller = self._control_manager.active_controller
                    self.socketio.emit('control_changed', {
                        'new_controller': new_controller,
                        'timestamp': time.time(),
                    })
                else:
                    emit('error', {'message': 'Cannot approve takeover'})

        @self.socketio.on('deny_takeover')
        def handle_deny_takeover():
            """Handle denial of takeover request."""
            sid = request.sid

            if self._control_manager:
                # Get the requester before canceling so we can notify them
                requester = self._control_manager.get_pending_requester()
                if self._control_manager.cancel_takeover(sid):
                    # Notify the controller (who denied)
                    emit('takeover_denied', {'message': 'Takeover denied'})
                    # Notify the requester that their request was denied
                    if requester:
                        self.socketio.emit(
                            'takeover_denied',
                            {'message': 'Your takeover request was denied'},
                            room=requester
                        )

        @self.socketio.on('take_photo')
        def handle_take_photo():
            """Handle photo capture request."""
            if self._frame_callback:
                frame = self._frame_callback()
                if frame:
                    try:
                        # Ensure directory exists
                        os.makedirs(self._photo_directory, exist_ok=True)

                        # Create safe filename
                        import datetime
                        filename = f"Photo_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(self._photo_directory, filename)

                        # Validate path
                        base_dir = os.path.abspath(self._photo_directory)
                        abs_path = os.path.abspath(filepath)
                        if os.path.commonpath([abs_path, base_dir]) != base_dir:
                            raise ValueError("Invalid photo path")

                        # Save photo
                        with open(filepath, 'wb') as f:
                            f.write(frame)

                        emit('photo_saved', {'path': filepath, 'filename': filename})

                    except (IOError, OSError, ValueError) as e:
                        _logger.exception("Failed to save photo")
                        emit('error', {'message': 'Failed to save photo'})
                else:
                    emit('error', {'message': 'No frame available'})
            else:
                emit('error', {'message': 'Camera not available'})

        @self.socketio.on('request_telemetry')
        def handle_request_telemetry():
            """Handle one-time telemetry request."""
            self._send_telemetry(request.sid)

    def _set_motors(self, left: float, right: float) -> None:
        """Set motor powers with safety limits.

        Args:
            left: Left motor power (-1.0 to 1.0)
            right: Right motor power (-1.0 to 1.0)
        """
        with self._motor_lock:
            # Clamp values
            left = max(-1.0, min(1.0, left))
            right = max(-1.0, min(1.0, right))

            # Apply power limit
            left *= self._max_power
            right *= self._max_power

            self._current_left = left
            self._current_right = right

            # Call motor callback
            if self._motor_callback:
                try:
                    self._motor_callback(left, right)
                except Exception as e:
                    _logger.exception("Motor callback error")

    def _send_telemetry(self, sid: Optional[str] = None) -> None:
        """Send telemetry data to client(s).

        Args:
            sid: Specific client to send to, or None for broadcast
        """
        telemetry = {
            'timestamp': time.time(),
            'motor_left': self._current_left,
            'motor_right': self._current_right,
            'speed_multiplier': self._speed_multiplier,
            'emergency_stopped': self._emergency_stop.is_stopped if self._emergency_stop else False,
        }

        # Add custom telemetry
        if self._telemetry_callback:
            try:
                custom = self._telemetry_callback()
                if custom:
                    telemetry.update(custom)
            except Exception as e:
                _logger.exception("Telemetry callback error")

        if sid:
            self.socketio.emit('telemetry', telemetry, room=sid)
        else:
            self.socketio.emit('telemetry', telemetry)

    def _telemetry_loop(self) -> None:
        """Background thread for periodic telemetry broadcast."""
        while self._telemetry_running:
            try:
                self._send_telemetry()
            except Exception as e:
                _logger.exception("Telemetry loop error")
            time.sleep(self._telemetry_interval)

    def _watchdog_loop(self) -> None:
        """Background thread for connection watchdog."""
        while self._telemetry_running:
            try:
                now = time.time()
                timed_out = []

                for sid, last_time in list(self._last_command_time.items()):
                    if now - last_time > self._watchdog_timeout:
                        timed_out.append(sid)

                # Stop motors if any active client timed out
                if timed_out and (self._current_left != 0.0 or self._current_right != 0.0):
                    _logger.warning("Watchdog timeout - stopping motors")
                    self._set_motors(0.0, 0.0)

                # Clean up timed-out entries to prevent memory leak
                for sid in timed_out:
                    del self._last_command_time[sid]

            except Exception as e:
                _logger.exception("Watchdog loop error")
            time.sleep(0.1)

    def start_telemetry(self) -> None:
        """Start background telemetry and watchdog threads."""
        if not self._telemetry_running:
            self._telemetry_running = True

            # Start telemetry thread
            self._telemetry_thread = threading.Thread(
                target=self._telemetry_loop,
                daemon=True,
                name="telemetry-loop"
            )
            self._telemetry_thread.start()

            # Start watchdog thread
            self._watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                daemon=True,
                name="watchdog-loop"
            )
            self._watchdog_thread.start()

    def stop_telemetry(self) -> None:
        """Stop background telemetry and watchdog threads."""
        self._telemetry_running = False
        if self._telemetry_thread:
            self._telemetry_thread.join(timeout=1.0)
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=1.0)

    def run(
        self,
        host: str = '127.0.0.1',
        port: int = 8080,
        debug: bool = False,
    ) -> None:
        """Run the web server.

        Args:
            host: Host address to bind to
            port: Port number to listen on
            debug: Enable Flask debug mode
        """
        _logger.info("Starting web server on %s:%d", host, port)

        if host == '0.0.0.0':
            _logger.warning("Server exposed on ALL interfaces - SECURITY RISK!")

        self.start_telemetry()

        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,
                log_output=True,
            )
        finally:
            self.stop_telemetry()
            self._set_motors(0.0, 0.0)
