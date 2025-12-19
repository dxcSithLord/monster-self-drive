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
from picamera2 import Picamera2
from libcamera import Transform

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

# ThunderBorg motor controller
TB = None

# Safety systems
emergency_stop = None
control_manager = None


# =========================================================================
# Camera Processing (picamera2)
# =========================================================================
class CameraCapture(threading.Thread):
    """Capture video stream from camera using picamera2."""

    def __init__(self, width=640, height=480, framerate=30,
                 flipped=True, jpeg_quality=80):
        super().__init__(daemon=True)
        self.width = width
        self.height = height
        self.framerate = framerate
        self.flipped = flipped
        self.jpeg_quality = jpeg_quality
        self.terminated = False
        self.picam2 = None

    def run(self):
        global lastFrame

        _logger.info("Initializing picamera2")
        self.picam2 = Picamera2()

        # Configure camera with transform for flipping
        transform = Transform(vflip=self.flipped, hflip=self.flipped)
        config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"},
            transform=transform,
            controls={"FrameRate": self.framerate}
        )
        self.picam2.configure(config)
        self.picam2.start()

        _logger.info("Camera capture started")

        while not self.terminated:
            try:
                # Capture frame as numpy array (RGB format)
                frame = self.picam2.capture_array()

                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                # Encode to JPEG
                retval, jpeg = cv2.imencode(
                    '.jpg', frame_bgr,
                    [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                )

                if retval:
                    with lockFrame:
                        lastFrame = jpeg.tobytes()

                # Rate limit to approximately target framerate
                time.sleep(1.0 / self.framerate)

            except Exception as e:
                _logger.error("Camera capture error: %s", e)
                time.sleep(0.1)

        _logger.info("Camera capture stopped")

    def stop(self):
        """Stop the camera capture."""
        self.terminated = True
        if self.picam2:
            self.picam2.stop()
            self.picam2.close()


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
    global running, TB, emergency_stop, control_manager

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

    # Load settings from config
    Settings.load()

    # Start camera capture thread (uses picamera2)
    _logger.info("Starting camera capture")
    capture_thread = CameraCapture(
        width=Settings.cameraWidth,
        height=Settings.cameraHeight,
        framerate=Settings.frameRate,
        flipped=Settings.flippedImage,
        jpeg_quality=Settings.jpegQuality
    )
    capture_thread.start()

    # Wait for camera to warm up
    time.sleep(2)

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

        # Stop camera capture
        capture_thread.stop()
        capture_thread.join(timeout=2)

        _logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
