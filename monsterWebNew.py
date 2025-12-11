#!/usr/bin/env python
# coding: utf-8
"""MonsterBorg Mobile Web Interface - Flask-SocketIO Version.

This is the Phase 1 implementation of the mobile-optimized web interface.
It replaces the legacy monsterWeb.py with Flask-SocketIO for real-time
WebSocket communication.

Features:
- Responsive design for mobile devices
- Touch controls with continuous movement
- Virtual joystick
- WebSocket real-time communication
- Battery/connection status indicators
- Emergency stop (accessible to any user)
- Single-user control model (ADR-004)

Usage:
    python monsterWebNew.py

See Also:
    - docs/DECISIONS.md: ADR-001 for WebSocket library decision
    - docs/IMPLEMENTATION_PLAN.md: Phase 1 specification
"""

import logging
import os
import sys
import threading
import time

import cv2
import picamera
import picamera.array

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ThunderBorg
from src.core.settings import Settings
from src.safety.control_manager import ControlManager
from src.safety.emergency_stop import EmergencyStop
from src.web import MonsterWebServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

# =========================================================================
# Global state
# =========================================================================
running = True
lastFrame = None
lockFrame = threading.Lock()
camera = None
processor = None

# ThunderBorg motor controller
TB = None

# Safety systems
emergency_stop = None
control_manager = None


# =========================================================================
# Camera Processing
# =========================================================================
class StreamProcessor(threading.Thread):
    """Process camera frames and encode to JPEG."""

    def __init__(self, camera_instance, flipped=True, jpeg_quality=80):
        super().__init__(daemon=True)
        self.camera = camera_instance
        self.stream = picamera.array.PiRGBArray(camera_instance)
        self.event = threading.Event()
        self.terminated = False
        self.flipped = flipped
        self.jpeg_quality = jpeg_quality
        self.start()

    def run(self):
        global lastFrame

        while not self.terminated:
            if self.event.wait(1):
                try:
                    self.stream.seek(0)
                    frame = self.stream.array

                    if self.flipped:
                        frame = cv2.flip(frame, -1)

                    retval, jpeg = cv2.imencode(
                        '.jpg', frame,
                        [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                    )

                    if retval:
                        with lockFrame:
                            lastFrame = jpeg.tobytes()

                finally:
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()


class ImageCapture(threading.Thread):
    """Capture video stream from camera."""

    def __init__(self, camera_instance, processor_instance):
        super().__init__(daemon=True)
        self.camera = camera_instance
        self.processor = processor_instance
        self.start()

    def run(self):
        _logger.info("Starting camera capture")
        self.camera.capture_sequence(
            self._trigger_stream(),
            format='bgr',
            use_video_port=True
        )
        _logger.info("Camera capture stopped")
        self.processor.terminated = True
        self.processor.join()

    def _trigger_stream(self):
        # running is read-only at module scope, no global needed
        while running:
            if self.processor.event.is_set():
                time.sleep(0.01)
            else:
                yield self.processor.stream
                self.processor.event.set()


# =========================================================================
# Callbacks for Web Server
# =========================================================================
def set_motors(left: float, right: float) -> None:
    """Set motor powers (callback for web server).

    Note: Power limiting is handled by MonsterWebServer's max_power parameter,
    so this callback receives pre-scaled values in range -max_power to +max_power.

    Args:
        left: Left motor power (pre-scaled by server's max_power)
        right: Right motor power (pre-scaled by server's max_power)
    """
    # TB is read-only at module scope, no global needed
    if TB is None:
        return

    # Check emergency stop
    if emergency_stop and emergency_stop.is_stopped:
        TB.MotorsOff()
        return

    # Set motor speeds (Motor1 = right, Motor2 = left)
    # Note: Power scaling already applied by MonsterWebServer._set_motors()
    TB.SetMotor1(right)
    TB.SetMotor2(left)


def get_frame() -> bytes:
    """Get current camera frame (callback for web server).

    Returns:
        JPEG-encoded frame as bytes, or None
    """
    # lastFrame and lockFrame are read-only at module scope, no global needed
    with lockFrame:
        return lastFrame


def get_telemetry() -> dict:
    """Get telemetry data (callback for web server).

    Returns:
        Dict with telemetry values
    """
    # TB is read-only at module scope, no global needed
    telemetry = {}

    if TB is not None:
        try:
            telemetry['battery_voltage'] = TB.GetBatteryReading()
        except Exception:
            telemetry['battery_voltage'] = 0.0

    return telemetry


def motor_stop_callback() -> None:
    """Emergency stop motor callback."""
    # TB is read-only at module scope, no global needed
    if TB is not None:
        TB.MotorsOff()
        TB.SetLedShowBattery(False)
        TB.SetLeds(1, 0, 0)  # Red LED


def on_emergency_state_change(is_stopped: bool, _reason: str) -> None:
    """Callback when emergency stop state changes."""
    # TB is read-only at module scope, no global needed
    if TB is not None:
        if is_stopped:
            TB.SetLeds(1, 0, 0)  # Red
        else:
            TB.SetLedShowBattery(True)


# =========================================================================
# Main
# =========================================================================
def main():
    global running, camera, processor, TB, emergency_stop, control_manager

    _logger.info("MonsterBorg Mobile Web Interface starting...")

    # Initialize ThunderBorg
    _logger.info("Initializing ThunderBorg")
    TB = ThunderBorg.ThunderBorg()
    TB.Init()

    if not TB.foundChip:
        boards = ThunderBorg.ScanForThunderBorg()
        if len(boards) == 0:
            _logger.error("No ThunderBorg found!")
        else:
            _logger.error("No ThunderBorg at address %02X, found: %s",
                         TB.i2cAddress, boards)
        sys.exit(1)

    # Configure ThunderBorg
    TB.SetCommsFailsafe(False)
    TB.SetLedShowBattery(False)
    TB.SetLeds(0, 0, 1)  # Blue LED = starting

    # Initialize safety systems
    _logger.info("Initializing safety systems")
    emergency_stop = EmergencyStop(
        motor_stop_callback=motor_stop_callback,
        on_state_change=on_emergency_state_change
    )

    control_manager = ControlManager()

    # Initialize camera
    _logger.info("Initializing camera")
    camera = picamera.PiCamera()
    camera.resolution = (Settings.cameraWidth, Settings.cameraHeight)
    camera.framerate = Settings.frameRate

    # Start stream processor
    _logger.info("Starting stream processor")
    processor = StreamProcessor(
        camera,
        flipped=Settings.flippedImage,
        jpeg_quality=Settings.jpegQuality
    )

    # Wait for camera to warm up
    time.sleep(2)

    # Start image capture
    _logger.info("Starting image capture")
    capture_thread = ImageCapture(camera, processor)

    # Create web server
    _logger.info("Creating web server")
    web_server = MonsterWebServer(
        motor_callback=set_motors,
        frame_callback=get_frame,
        telemetry_callback=get_telemetry,
        emergency_stop=emergency_stop,
        control_manager=control_manager,
        photo_directory=Settings.photoDirectory,
        max_power=Settings.voltageOut / Settings.voltageIn,
    )

    # Set LED to green = ready
    TB.SetLedShowBattery(True)

    # Run web server
    _logger.info("Starting web server on %s:%d",
                Settings.webBindAddress, Settings.webPort)

    if Settings.webBindAddress == '0.0.0.0':
        _logger.warning("Server exposed on ALL interfaces - SECURITY RISK!")

    try:
        web_server.run(
            host=Settings.webBindAddress,
            port=Settings.webPort,
            debug=False
        )
    except KeyboardInterrupt:
        _logger.info("Shutdown requested")
    finally:
        # Cleanup
        _logger.info("Shutting down...")
        running = False

        # Stop motors
        TB.MotorsOff()
        TB.SetLedShowBattery(False)
        TB.SetLeds(0, 0, 0)

        # Wait for threads
        capture_thread.join(timeout=2)
        processor.terminated = True
        processor.join(timeout=2)

        # Close camera
        del camera

        _logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
