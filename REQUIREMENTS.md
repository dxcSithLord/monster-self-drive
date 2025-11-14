# MonsterBorg Self-Drive Project Requirements

**Version**: 2.0
**Date**: 2025-11-14
**Target Platform**: Raspberry Pi 3B
**Python Version**: 3.11+ (3.12 recommended)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Requirements](#system-requirements)
3. [Functional Requirements](#functional-requirements)
4. [Technical Requirements](#technical-requirements)
5. [Performance Requirements](#performance-requirements)
6. [Safety Requirements](#safety-requirements)
7. [User Interface Requirements](#user-interface-requirements)
8. [Data Requirements](#data-requirements)
9. [Deployment Requirements](#deployment-requirements)
10. [Testing Requirements](#testing-requirements)

---

## Executive Summary

The MonsterBorg Self-Drive Project aims to create an intelligent, mobile-controlled robot capable of:
- Manual control via mobile web interface
- Autonomous line following
- Intelligent object tracking and following
- Re-acquisition of lost targets
- Operation in both normal and inverted orientations

This document defines the requirements for Version 2.0, which adds mobile web controls and advanced object tracking capabilities to the existing line-following functionality.

---

## System Requirements

### Hardware Requirements

#### Minimum Required Hardware
- **Raspberry Pi 3B** (or newer: 3B+, 4, 5)
  - ARMv7/ARMv8 processor
  - Minimum 1GB RAM
  - 8GB+ microSD card
  - WiFi capability (built-in or USB adapter)

- **Pi Camera Module** (v1, v2, or HQ)
  - Minimum resolution: 640x480
  - Recommended: 1280x720 or higher
  - Frame rate: 30 fps minimum

- **ThunderBorg Motor Controller**
  - I2C interface
  - Dual motor control
  - 9V+ battery power

- **MonsterBorg Chassis**
  - 4-wheel drive configuration
  - All-terrain wheels
  - Battery holder (2S LiPo or 6x AA)

#### Recommended Additional Hardware
- **IMU Module** (for orientation detection)
  - MPU6050 (6-axis: accelerometer + gyroscope)
  - OR BNO055 (9-axis: accel + gyro + magnetometer)
  - I2C interface
  - Cost: $5-15

- **Ultrasonic Distance Sensor** (optional, for backup distance measurement)
  - HC-SR04 or similar
  - Range: 2cm - 400cm
  - GPIO interface

- **Wheel Encoders** (optional, for accurate odometry)
  - Optical or magnetic encoders
  - Interrupt-capable GPIO pins

### Software Requirements

#### Operating System
- **Primary**: Raspberry Pi OS (Debian-based)
  - Version: Bullseye (11) or newer
  - Bookworm (12) recommended
  - 64-bit preferred for performance

- **Alternative**: Ubuntu 22.04 LTS or newer
  - Must support Raspberry Pi 3B
  - ARM architecture support required

#### Python Environment
- **Python Version**: 3.11 minimum, 3.12+ recommended
- **Virtual Environment**: Recommended (venv or conda)
- **Package Manager**: pip 23.0+

#### System Libraries
```bash
# Camera support
libcamera-dev
libcamera-tools
python3-picamera2

# OpenCV dependencies
libopencv-dev
libatlas-base-dev
libjasper-dev
libqt4-test
libhdf5-dev

# I2C tools
i2c-tools
libi2c-dev
python3-smbus

# Web server
libssl-dev
libffi-dev
```

---

## Functional Requirements

### FR1: Mobile Web Control Interface

#### FR1.1: Responsive Design
**Priority**: High
**Description**: Web interface must be fully functional on mobile devices (phones and tablets).

**Acceptance Criteria**:
- [ ] Interface adapts to screen sizes from 320px to 2048px width
- [ ] Portrait and landscape orientations supported
- [ ] Touch targets minimum 44x44px (Apple HIG standard)
- [ ] No horizontal scrolling required
- [ ] Text remains legible at all sizes (minimum 16px body text)

#### FR1.2: Touch Controls
**Priority**: High
**Description**: Controls must be optimized for touch input.

**Acceptance Criteria**:
- [ ] Touch and hold to move (release to stop)
- [ ] Visual feedback on touch (button state changes)
- [ ] No accidental double-tap zoom
- [ ] Swipe gestures do not interfere with controls
- [ ] Multi-touch support for simultaneous inputs (e.g., move + camera)

#### FR1.3: Virtual Joystick
**Priority**: Medium
**Description**: Optional analog control via virtual joystick.

**Acceptance Criteria**:
- [ ] Joystick provides continuous speed/direction control
- [ ] Dead zone configurable (default 10%)
- [ ] Auto-centering when released
- [ ] Visual feedback showing joystick position
- [ ] Sensitivity adjustment available

#### FR1.4: Connection Management
**Priority**: High
**Description**: Reliable connection with automatic recovery.

**Acceptance Criteria**:
- [ ] WebSocket connection with automatic reconnection
- [ ] Connection status indicator (connected/disconnected/reconnecting)
- [ ] Graceful degradation to HTTP if WebSocket unavailable
- [ ] Watchdog timer stops motors on connection loss (max 2 seconds)
- [ ] Connection timeout configurable

#### FR1.5: Real-time Telemetry Display
**Priority**: Medium
**Description**: Display robot status and sensor data in real-time.

**Acceptance Criteria**:
- [ ] Battery voltage display (updated every 1 second)
- [ ] Current speed display (updated every 100ms)
- [ ] Operation mode indicator (Manual/Line Follow/Object Track/Idle)
- [ ] Orientation status (Normal/Inverted)
- [ ] Tracking status when in Object Follow mode
- [ ] Distance to target (when tracking)
- [ ] Frame rate / latency indicator

### FR2: Object Detection and Tracking

#### FR2.1: Object Selection
**Priority**: High
**Description**: User must be able to select object to track via web interface.

**Acceptance Criteria**:
- [ ] Tap/click on video stream to select object
- [ ] Bounding box drawn around selected object
- [ ] Confirmation prompt before starting tracking
- [ ] Ability to cancel and reselect
- [ ] Selection coordinates accurately mapped from display to camera frame

#### FR2.2: Tracking Algorithms
**Priority**: High
**Description**: Multiple tracking algorithms for robustness.

**Acceptance Criteria**:
- [ ] **KCF Tracker**: Fast, efficient (primary method)
- [ ] **CSRT Tracker**: More accurate fallback
- [ ] **Template Matching**: Simple fallback for re-acquisition
- [ ] **Color-based Tracking**: For distinctly colored objects
- [ ] Automatic algorithm selection based on object characteristics
- [ ] Manual algorithm override available

#### FR2.3: Tracking Confidence
**Priority**: Medium
**Description**: System must estimate tracking quality.

**Acceptance Criteria**:
- [ ] Confidence score (0-100%) calculated each frame
- [ ] Score based on: template correlation, feature count, motion consistency
- [ ] Low confidence triggers re-acquisition (threshold: 30%)
- [ ] Confidence displayed on web interface
- [ ] Confidence history logged for analysis

#### FR2.4: Object Classification (Optional)
**Priority**: Low
**Description**: Identify object type (person, animal, vehicle).

**Acceptance Criteria**:
- [ ] TensorFlow Lite model for classification
- [ ] Support for COCO dataset classes (person, cat, dog, car, etc.)
- [ ] Classification displayed on interface
- [ ] Configurable confidence threshold (default: 50%)
- [ ] Falls back to generic tracking if classification unavailable

### FR3: Distance Estimation and Following

#### FR3.1: Distance Estimation
**Priority**: High
**Description**: Estimate distance to tracked object.

**Acceptance Criteria**:
- [ ] Distance calculated from bounding box size
- [ ] Calibration procedure for different object types
- [ ] Distance accuracy: ±20% at 0.5-3.0 meters
- [ ] Distance updated every frame (30 Hz)
- [ ] Alternative: ultrasonic sensor integration for ground truth

#### FR3.2: Safe Following Distance
**Priority**: Critical (Safety)
**Description**: Maintain safe distance from target.

**Acceptance Criteria**:
- [ ] Target distance configurable (default: 1.5m)
- [ ] Minimum safe distance enforced (default: 0.5m)
- [ ] Maximum distance before speedup (default: 3.0m)
- [ ] Emergency stop if distance < 0.3m
- [ ] Speed reduction proportional to distance error

#### FR3.3: Speed Matching
**Priority**: High
**Description**: Match speed of moving target.

**Acceptance Criteria**:
- [ ] Object velocity estimated from frame-to-frame motion
- [ ] MonsterBorg speed adjusted to match object velocity
- [ ] PID controller for smooth speed transitions (no jerking)
- [ ] Maximum follow speed limit (default: 80% of max)
- [ ] Acceleration limited to prevent wheel slip

#### FR3.4: Steering Control
**Priority**: High
**Description**: Keep object centered in camera view.

**Acceptance Criteria**:
- [ ] Object kept within center 40% of frame width
- [ ] Smooth steering (no oscillation)
- [ ] PID tuning for different terrains
- [ ] Maximum steering rate limited
- [ ] Differential drive calculation accurate

### FR4: Re-acquisition Algorithm

#### FR4.1: Object Loss Detection
**Priority**: High
**Description**: Detect when tracking is lost.

**Acceptance Criteria**:
- [ ] Trigger on tracker failure
- [ ] Trigger on confidence < 30%
- [ ] Trigger on bounding box out of frame
- [ ] Trigger on sudden size change > 50% (occlusion)
- [ ] Time-to-trigger configurable (default: 0.5s)

#### FR4.2: Multi-Stage Search
**Priority**: High
**Description**: Systematic search for lost object.

**Acceptance Criteria**:
- [ ] **Stage 1 - Local Search** (0-5s): Scan ±30 degrees from last direction
- [ ] **Stage 2 - Expanded Search** (5-15s): 360-degree rotation scan
- [ ] **Stage 3 - Return** (15+s): Navigate back to last known position
- [ ] Each stage timeout configurable
- [ ] Search pattern visualization on web interface

#### FR4.3: Position Tracking (Odometry)
**Priority**: High
**Description**: Track robot position for return-to-position.

**Acceptance Criteria**:
- [ ] Dead reckoning from motor speeds
- [ ] Position accuracy: ±10% of distance traveled
- [ ] Heading accuracy: ±5 degrees
- [ ] Optional: IMU integration for improved accuracy
- [ ] Optional: Wheel encoder integration
- [ ] Position reset on tracking start

#### FR4.4: Return to Last Position
**Priority**: Medium
**Description**: Navigate back to where object was lost.

**Acceptance Criteria**:
- [ ] Calculate path from current to last position
- [ ] Rotate to correct heading
- [ ] Drive to position (straight line path)
- [ ] Orient to original heading
- [ ] Accuracy: Within 0.5m of original position
- [ ] Timeout: 60 seconds maximum

#### FR4.5: Waiting State
**Priority**: Medium
**Description**: Wait for object to reappear or user input.

**Acceptance Criteria**:
- [ ] Motors stopped
- [ ] Camera continues scanning
- [ ] Object detection active (any movement triggers re-acquisition)
- [ ] Timeout: 5 minutes (then return to Idle mode)
- [ ] User can cancel wait and return to manual control

### FR5: Inverted Operation

#### FR5.1: Orientation Detection
**Priority**: High
**Description**: Detect if robot is upside down.

**Acceptance Criteria**:
- [ ] **Method 1 - IMU**: Use accelerometer Z-axis (preferred)
- [ ] **Method 2 - Manual Toggle**: User button on interface
- [ ] **Method 3 - Image Analysis**: Horizon detection (fallback)
- [ ] Detection latency < 100ms
- [ ] False positive rate < 1%

#### FR5.2: Motor Control Inversion
**Priority**: High
**Description**: Reverse motor commands when inverted.

**Acceptance Criteria**:
- [ ] Motor directions reversed when inverted detected
- [ ] Left/right motors swapped
- [ ] Forward/backward reversed
- [ ] Steering calculations adjusted
- [ ] Smooth transition during flip (no sudden movements)

#### FR5.3: Camera Orientation
**Priority**: Medium
**Description**: Correct camera image orientation.

**Acceptance Criteria**:
- [ ] Image rotated 180° when inverted
- [ ] Rotation applied before processing
- [ ] No performance degradation (<5ms per frame)
- [ ] Rotation state saved for session

#### FR5.4: Tracking Continuity
**Priority**: Medium
**Description**: Maintain tracking through orientation changes.

**Acceptance Criteria**:
- [ ] Tracking paused during flip (0.5-1s)
- [ ] Tracker re-initialized with corrected image
- [ ] Object re-detected within 2 seconds
- [ ] Falls back to re-acquisition if detection fails
- [ ] User notified of orientation change

### FR6: Mode Selection and Integration

#### FR6.1: Operating Modes
**Priority**: High
**Description**: Support multiple operation modes.

**Modes**:
1. **IDLE**: Motors off, awaiting commands
2. **MANUAL**: Direct web interface control
3. **LINE_FOLLOW**: Autonomous line following (existing)
4. **OBJECT_FOLLOW**: Object tracking and following (new)

**Acceptance Criteria**:
- [ ] Only one mode active at a time
- [ ] Clean state transitions (resources released/acquired)
- [ ] Emergency stop works in all modes
- [ ] Mode displayed prominently on interface
- [ ] Mode change confirmation required for autonomous modes

#### FR6.2: Mode Switching
**Priority**: High
**Description**: Seamless mode transitions.

**Acceptance Criteria**:
- [ ] Mode selector dropdown on web interface
- [ ] Confirmation prompt for autonomous modes
- [ ] Motors stopped during transition
- [ ] Resources properly released (camera, threads)
- [ ] Transition time < 2 seconds
- [ ] Error handling for failed transitions

#### FR6.3: Configuration Persistence
**Priority**: Low
**Description**: Save settings between sessions.

**Acceptance Criteria**:
- [ ] Last mode saved to config file
- [ ] PID parameters saved
- [ ] Distance thresholds saved
- [ ] Camera settings saved
- [ ] Auto-load on startup (optional)

---

## Technical Requirements

### TR1: Software Architecture

#### TR1.1: Modularity
**Priority**: High
**Description**: Code must be modular and maintainable.

**Acceptance Criteria**:
- [ ] Separate modules for: Web Server, Motor Control, Vision, Tracking, Navigation
- [ ] Clear interfaces between modules
- [ ] Dependency injection where appropriate
- [ ] Single Responsibility Principle followed
- [ ] Maximum file size: 500 lines (guideline)

#### TR1.2: Threading Model
**Priority**: High
**Description**: Efficient multi-threaded architecture.

**Acceptance Criteria**:
- [ ] Separate threads for: Camera, Processing, Control, Web Server
- [ ] Thread-safe communication (queues, locks, events)
- [ ] No busy-waiting loops
- [ ] Graceful thread shutdown
- [ ] Thread exception handling

#### TR1.3: Error Handling
**Priority**: High
**Description**: Robust error handling and recovery.

**Acceptance Criteria**:
- [ ] Try-except blocks for all I/O operations
- [ ] Graceful degradation (continue with reduced functionality)
- [ ] Error logging to file
- [ ] User notification of critical errors
- [ ] Automatic recovery where possible

#### TR1.4: Logging
**Priority**: Medium
**Description**: Comprehensive logging for debugging and analysis.

**Acceptance Criteria**:
- [ ] Python logging module used (not print statements)
- [ ] Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- [ ] Configurable log level
- [ ] Log rotation (max 10MB per file, keep 5 files)
- [ ] Timestamps and thread IDs in logs

### TR2: Performance Optimization

#### TR2.1: Image Processing
**Priority**: High
**Description**: Optimize for Raspberry Pi 3B performance.

**Acceptance Criteria**:
- [ ] Frame rate: 30 fps minimum
- [ ] Processing latency: <50ms per frame
- [ ] CPU usage: <80% average
- [ ] Memory usage: <400MB
- [ ] Thermal throttling avoided (<80°C)

**Optimization Techniques**:
- [ ] Downscale images (320x240 or 160x120 for processing)
- [ ] Use grayscale where possible
- [ ] NumPy vectorized operations
- [ ] Limit tracking search region
- [ ] Frame skipping if CPU overloaded

#### TR2.2: Network Optimization
**Priority**: Medium
**Description**: Efficient web communication.

**Acceptance Criteria**:
- [ ] Video stream compression (JPEG quality: 70-85%)
- [ ] Adaptive bitrate based on connection
- [ ] WebSocket message batching (10Hz telemetry)
- [ ] Bandwidth usage: <2 Mbps for video
- [ ] Latency: <200ms for controls

#### TR2.3: Power Efficiency
**Priority**: Low
**Description**: Maximize battery life.

**Acceptance Criteria**:
- [ ] Idle mode reduces camera frame rate
- [ ] WiFi power saving enabled
- [ ] HDMI disabled (headless mode)
- [ ] CPU governor: ondemand or conservative
- [ ] Battery life: >30 minutes continuous operation

### TR3: Code Quality

#### TR3.1: Python Standards
**Priority**: High
**Description**: Follow Python best practices.

**Acceptance Criteria**:
- [ ] PEP 8 compliant (via Black formatter)
- [ ] Type hints for function signatures
- [ ] Docstrings for all public functions/classes
- [ ] Google or NumPy docstring style
- [ ] Flake8 linting passes

#### TR3.2: Version Control
**Priority**: High
**Description**: Git best practices.

**Acceptance Criteria**:
- [ ] Feature branches for new development
- [ ] Meaningful commit messages (conventional commits)
- [ ] No secrets in repository
- [ ] .gitignore for build artifacts
- [ ] Tagged releases (semantic versioning)

#### TR3.3: Documentation
**Priority**: Medium
**Description**: Comprehensive documentation.

**Acceptance Criteria**:
- [ ] README with setup instructions
- [ ] Installation guide for Raspberry Pi
- [ ] User manual for web interface
- [ ] API documentation (Sphinx)
- [ ] Troubleshooting guide

---

## Performance Requirements

### PF1: Real-time Operation
- **Camera Frame Rate**: 30 fps minimum, 60 fps preferred
- **Processing Latency**: <50ms from capture to motor command
- **Control Loop Frequency**: 20 Hz minimum
- **Web Interface Latency**: <200ms for user inputs

### PF2: Accuracy
- **Distance Estimation**: ±20% at 0.5-3.0m range
- **Tracking Precision**: Object kept within center 40% of frame
- **Odometry**: ±10% distance error, ±5° heading error
- **Steering Accuracy**: ±5% of commanded value

### PF3: Reliability
- **Uptime**: 99% during operation (minimal crashes)
- **Tracking Success Rate**: 90% in favorable conditions
- **Re-acquisition Success**: 70% within 15 seconds
- **Connection Reliability**: Auto-reconnect within 5 seconds

### PF4: Scalability
- **Multiple Clients**: Support 3 simultaneous web connections
- **Video Streaming**: 5 concurrent viewers at reduced quality
- **Configuration**: Support 10+ saved tracking profiles

---

## Safety Requirements

### SF1: Collision Avoidance
**Priority**: Critical

- [ ] Emergency stop if distance < 0.3m (configurable)
- [ ] Speed reduction when approaching obstacles
- [ ] Maximum speed limit configurable (default: 80%)
- [ ] Obstacle detection timeout (stop if no valid distance reading)

### SF2: Connection Failsafe
**Priority**: Critical

- [ ] Motors stop within 2 seconds of connection loss
- [ ] Audible/visual warning before stopping
- [ ] Automatic reconnection attempts
- [ ] Manual override requires connection restore

### SF3: Battery Protection
**Priority**: High

- [ ] Low battery warning at 7.2V (configurable)
- [ ] Critical battery shutdown at 6.8V
- [ ] Speed reduction at low battery
- [ ] Battery voltage displayed continuously

### SF4: Thermal Protection
**Priority**: High

- [ ] CPU temperature monitoring
- [ ] Throttling at 75°C
- [ ] Shutdown at 85°C
- [ ] Warning displayed on interface

### SF5: Emergency Stop
**Priority**: Critical

- [ ] Dedicated emergency stop button (always visible)
- [ ] Keyboard shortcut (spacebar)
- [ ] Physical button option (GPIO pin)
- [ ] Stops all motors immediately
- [ ] Requires manual restart

---

## User Interface Requirements

### UI1: Mobile Web Interface

#### UI1.1: Layout
- **Header**: Logo, battery, connection status
- **Video Stream**: Full-width, 16:9 or 4:3 aspect ratio
- **Controls**: Below video or overlay (user preference)
- **Telemetry**: Collapsible panel
- **Settings**: Hamburger menu

#### UI1.2: Color Scheme
- **Theme**: Dark mode default (battery saving)
- **Light mode**: Optional toggle
- **Accent Color**: Green (active), Red (danger), Yellow (warning)
- **Contrast Ratio**: WCAG AA compliant (4.5:1 minimum)

#### UI1.3: Accessibility
- [ ] Touch targets minimum 44x44px
- [ ] Font size minimum 16px (body text)
- [ ] High contrast mode
- [ ] Screen reader support (ARIA labels)
- [ ] No color-only indicators

#### UI1.4: Responsiveness
- [ ] Breakpoints: 320px, 480px, 768px, 1024px
- [ ] Portrait and landscape layouts
- [ ] Flexbox/Grid layout (no fixed widths)
- [ ] Images/video scale proportionally

### UI2: Telemetry Dashboard
- **Battery Voltage**: Large, color-coded gauge
- **Speed**: Horizontal bar (current speed)
- **Distance to Target**: Numeric + bar chart
- **Tracking Status**: Icon + text (TRACKING / SEARCHING / LOST)
- **Orientation**: Icon (robot upright/inverted)
- **Frame Rate**: Small numeric indicator
- **Mode**: Prominent badge

### UI3: Settings Panel
- [ ] Mode selection dropdown
- [ ] Tracking algorithm selector
- [ ] Distance thresholds (sliders)
- [ ] PID gain adjustment (advanced)
- [ ] Camera settings (resolution, flip)
- [ ] Save/Load configuration profiles

---

## Data Requirements

### DR1: Configuration Data
**Storage**: JSON or INI file

**Fields**:
- `mode`: Current operating mode
- `tracking_algorithm`: KCF/CSRT/MOSSE/TEMPLATE
- `target_distance`: Meters
- `safe_min_distance`: Meters
- `safe_max_distance`: Meters
- `pid_gains`: Object with P, I, D values
- `camera_resolution`: Width x Height
- `camera_framerate`: FPS
- `camera_flip`: Boolean
- `inversion_detection`: IMU/MANUAL/IMAGE
- `websocket_port`: Port number

### DR2: Telemetry Data
**Frequency**: 10 Hz

**Fields**:
- `timestamp`: Unix timestamp (float)
- `mode`: String
- `tracking_status`: String
- `distance_to_target`: Float (meters)
- `object_bbox`: [x, y, width, height]
- `battery_voltage`: Float (volts)
- `speed_left`: Float (-1.0 to 1.0)
- `speed_right`: Float (-1.0 to 1.0)
- `orientation`: "NORMAL" / "INVERTED"
- `frame_rate`: Integer (fps)
- `cpu_temperature`: Float (°C)

### DR3: Logging Data
**Storage**: Rotating log files

**Format**: `[TIMESTAMP] [LEVEL] [MODULE] [THREAD] Message`

**Example**:
```
[2025-11-14 12:34:56.789] [INFO] [ObjectTracker] [Thread-3] Object acquired: bbox=(120, 80, 200, 180)
[2025-11-14 12:35:01.234] [WARNING] [DistanceEstimator] [Thread-3] Distance uncertain: confidence=0.42
```

### DR4: Calibration Data
**Storage**: JSON file

**Purpose**: Store calibration parameters for different objects/scenarios

**Structure**:
```json
{
  "distance_calibration": {
    "person_standing": {
      "reference_height_pixels": 200,
      "reference_distance_meters": 1.0
    },
    "ball_soccer": {
      "reference_height_pixels": 80,
      "reference_distance_meters": 2.0
    }
  },
  "odometry_calibration": {
    "wheelbase_meters": 0.15,
    "wheel_radius_meters": 0.05,
    "ticks_per_revolution": 20
  }
}
```

---

## Deployment Requirements

### DP1: Installation Process

#### DP1.1: Raspberry Pi Setup
```bash
# 1. Flash OS (Raspberry Pi OS Lite or Desktop)
# 2. Enable camera and I2C
sudo raspi-config

# 3. Update system
sudo apt-get update
sudo apt-get upgrade -y

# 4. Install system dependencies
sudo apt-get install -y python3 python3-pip python3-venv \
    libcamera-dev python3-picamera2 \
    i2c-tools python3-smbus \
    libopencv-dev libatlas-base-dev

# 5. Clone repository
git clone https://github.com/dxcSithLord/monster-self-drive.git
cd monster-self-drive

# 6. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 7. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 8. Configure settings
cp Settings.py.example Settings.py
# Edit Settings.py with your values

# 9. Test ThunderBorg connection
python3 ThunderBorg.py

# 10. Run web server
python3 monsterWeb.py
```

#### DP1.2: Startup Script
**File**: `/etc/systemd/system/monsterborg.service`

```ini
[Unit]
Description=MonsterBorg Self-Drive Web Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/monster-self-drive
ExecStart=/home/pi/monster-self-drive/venv/bin/python3 /home/pi/monster-self-drive/monsterWeb.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable**:
```bash
sudo systemctl enable monsterborg.service
sudo systemctl start monsterborg.service
```

### DP2: Network Configuration

#### DP2.1: WiFi Access Point (Optional)
- MonsterBorg creates its own WiFi network
- Users connect directly to robot
- No internet router required
- SSID: `MonsterBorg-XXXX` (X = last 4 of MAC)
- Password: Configurable (default: `monsterborg`)

#### DP2.2: Client Mode (Default)
- Connect to existing WiFi network
- Obtain IP via DHCP
- Announce via mDNS (monsterborg.local)
- Display IP on startup (if screen attached)

### DP3: Updates and Maintenance

#### DP3.1: Software Updates
- [ ] OTA (Over-The-Air) update capability
- [ ] Update button in web interface (admin mode)
- [ ] Automatic backup before update
- [ ] Rollback capability
- [ ] Update notifications

#### DP3.2: Backup and Restore
- [ ] Configuration backup to SD card
- [ ] Restore from backup
- [ ] Factory reset option
- [ ] Export logs via web interface

---

## Testing Requirements

### TS1: Unit Tests
**Coverage**: Minimum 70%

**Modules to Test**:
- [ ] `ObjectTracker`: Initialization, update, confidence calculation
- [ ] `DistanceEstimator`: Distance calculation, calibration
- [ ] `Odometry`: Position tracking, heading calculation
- [ ] `InvertedController`: Motor inversion logic
- [ ] `ReacquisitionStateMachine`: State transitions

**Framework**: pytest

### TS2: Integration Tests
- [ ] Web server communication (HTTP and WebSocket)
- [ ] Camera to tracking pipeline
- [ ] Tracking to motor control
- [ ] Mode switching
- [ ] Orientation detection to motor control

### TS3: Field Tests

#### TS3.1: Object Following
**Test Cases**:
1. Follow person walking straight (0.5, 1.0, 1.5 m/s)
2. Follow person turning (left, right, 90°, 180°)
3. Follow ball rolling (various speeds)
4. Follow another robot
5. Different lighting (indoor, outdoor, shadows, backlighting)

**Success Criteria**:
- Distance maintained within ±30cm
- No collisions
- Tracking continuous for >30 seconds

#### TS3.2: Re-acquisition
**Test Cases**:
1. Object moves behind obstacle (5s, 10s, 15s)
2. Object exits frame quickly
3. Multiple similar objects (select correct one)
4. Return-to-position accuracy

**Success Criteria**:
- Re-acquisition within time limits (70% success)
- Correct object identified (90% when unique)
- Return accuracy within 0.5m

#### TS3.3: Inversion
**Test Cases**:
1. Manual flip (gentle)
2. Ramp flip (drive up and over)
3. Tracking continuity during flip
4. Motor control correctness when inverted

**Success Criteria**:
- Orientation detected within 100ms
- Motors reverse correctly (100% of time)
- Tracking resumes within 2 seconds (80% success)

#### TS3.4: Mobile Interface
**Test Devices**:
- iPhone (Safari)
- Android phone (Chrome)
- iPad (Safari)
- Android tablet (Chrome)

**Test Scenarios**:
- Button controls (all directions)
- Virtual joystick (if implemented)
- Video stream playback
- Touch responsiveness
- Connection reliability

**Success Criteria**:
- All controls functional on all devices
- Video stream <500ms latency
- Touch response <100ms
- No UI glitches or overlaps

### TS4: Performance Tests
- [ ] Benchmark frame rate (30 fps minimum)
- [ ] Benchmark processing latency (<50ms)
- [ ] Memory leak test (24-hour run)
- [ ] CPU usage under load (<80%)
- [ ] Network bandwidth measurement (<2 Mbps)
- [ ] Battery life test (>30 minutes)

### TS5: Safety Tests
- [ ] Emergency stop response time (<500ms)
- [ ] Collision avoidance trigger distance
- [ ] Connection loss behavior (motors stop within 2s)
- [ ] Low battery handling
- [ ] Thermal throttling

---

## Acceptance Criteria

The MonsterBorg Self-Drive Project v2.0 will be considered **complete** when:

1. ✅ All **Critical** and **High** priority requirements are met
2. ✅ Mobile web interface is fully functional on iOS and Android
3. ✅ Object tracking achieves 90% success rate in favorable conditions
4. ✅ Re-acquisition succeeds 70% of the time within 15 seconds
5. ✅ Inverted operation is detected and handled correctly
6. ✅ All safety requirements are implemented and tested
7. ✅ Performance meets or exceeds specified benchmarks
8. ✅ Field tests pass on at least 2 mobile devices
9. ✅ Documentation is complete (README, user manual, installation guide)
10. ✅ Code quality standards are met (PEP 8, type hints, docstrings)

---

## Glossary

- **MonsterBorg**: 4WD robot platform from PiBorg
- **ThunderBorg**: Dual motor controller board
- **Pi Camera**: Raspberry Pi Camera Module
- **IMU**: Inertial Measurement Unit (accelerometer + gyroscope)
- **KCF**: Kernelized Correlation Filters (tracking algorithm)
- **CSRT**: Channel and Spatial Reliability Tracker
- **PID**: Proportional-Integral-Derivative controller
- **Odometry**: Position tracking from wheel/motor data
- **Dead Reckoning**: Position estimation without external references
- **Differential Drive**: Steering via different left/right wheel speeds
- **WebSocket**: Bi-directional communication protocol
- **OTA**: Over-The-Air (wireless updates)
- **mDNS**: Multicast DNS (e.g., monsterborg.local)

---

## Revision History

| Version | Date       | Author | Changes                          |
|---------|------------|--------|----------------------------------|
| 1.0     | 2024-XX-XX | -      | Initial line-following version   |
| 2.0     | 2025-11-14 | Claude | Mobile controls + object tracking|

---

## References

1. OpenCV Documentation: https://docs.opencv.org/
2. Raspberry Pi Documentation: https://www.raspberrypi.com/documentation/
3. PiBorg MonsterBorg Guide: https://www.piborg.org/monsterborg
4. Python Best Practices: PEP 8, PEP 257
5. Mobile Web Design: Apple HIG, Material Design Guidelines

---

**End of Requirements Document**
