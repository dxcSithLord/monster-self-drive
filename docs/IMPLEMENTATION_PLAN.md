# MonsterBorg Mobile Controls & Object Tracking Implementation Plan

## Project Overview

Upgrade the MonsterBorg web interface for mobile phone compatibility and add
intelligent object tracking with re-acquisition capabilities, including inverted
operation support.

---

## Phase 1: Mobile Web Interface Enhancement

### 1.1 Responsive Design

**Objective**: Make web controls work seamlessly on mobile devices

**Changes to `monsterWeb.py`**:

- Add responsive viewport meta tag
- Implement CSS media queries for mobile screens
- Optimize layout for portrait and landscape orientations
- Increase button sizes for touch interaction (minimum 44x44px)
- Add touch-friendly spacing between controls

**Implementation Details**:

```python
# HTML additions:
<meta name="viewport" content="width=device-width, initial-scale=1.0,
    maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
```

**CSS Enhancements**:

- Flexbox/Grid layout for adaptive positioning
- Larger buttons (60px+ for mobile)
- Touch-optimized spacing (16px minimum)
- Prevent text selection and zoom on double-tap
- Full-screen video stream option

### 1.2 Touch Controls

**Objective**: Replace click-based controls with touch-optimized interactions

**Features**:

- Touch and hold for continuous movement
- Release to stop (safety feature)
- Prevent accidental activation
- Visual feedback on touch
- Haptic feedback via Vibration API (where supported)

**Implementation**:

```javascript
// Touch events
element.addEventListener('touchstart', handleTouchStart);
element.addEventListener('touchend', handleTouchEnd);
element.addEventListener('touchmove', preventDefault); // Prevent scrolling
```

### 1.3 Virtual Joystick (Optional)

**Objective**: Provide intuitive analog control

**Library**: Use nipple.js or custom implementation

**Features**:

- Continuous speed/direction control
- Visual feedback
- Dead zone for stability
- Auto-centering
- Configurable sensitivity

**Joystick Mapping**:

```text
Y-axis: Forward/Backward speed (-1.0 to 1.0)
X-axis: Left/Right steering (-1.0 to 1.0)
```

### 1.4 WebSocket Communication (Upgrade)

**Objective**: Replace HTTP polling with real-time WebSocket connection

**Benefits**:

- Lower latency
- Reduced bandwidth
- Real-time telemetry
- Bi-directional communication

**Implementation**:

- Python: Use `websockets` library or Flask-SocketIO
- JavaScript: Native WebSocket API
- Fallback to HTTP for compatibility

### 1.5 Mobile UI Enhancements

**Additional Features**:

- Battery level indicator
- Speed indicator
- Connection status indicator
- Orientation lock option
- Fullscreen camera view toggle
- Emergency stop button (always visible)

---

## Phase 2: Object Detection & Tracking System

### 2.1 Architecture Overview

**New Module**: `ObjectTracker.py`

**Components**:

1. Object Detection Module
2. Object Tracking Module
3. Distance Estimation Module
4. Motion Controller
5. Re-acquisition Module
6. Inversion Detection Module

### 2.2 Object Detection Module

**Objective**: Identify and select objects to follow

**Methods**:

#### Option A: Template Matching (Simple, Fast)

```python
# User clicks on web interface to select object
# System captures template from current frame
# Uses cv2.matchTemplate() for tracking
```

**Pros**: No external dependencies, fast on RPi 3B
**Cons**: Sensitive to scale/rotation changes

#### Option B: Color-Based Detection (Current Track-Following Logic)

```python
# Extend existing color detection from ImageProcessor.py
# Allow user to select color range via web interface
# Track largest blob of specified color
```

**Pros**: Already implemented, robust
**Cons**: Limited to color-distinctive objects

#### Option C: Feature-Based Tracking (Recommended)

```python
# Use cv2.goodFeaturesToTrack() + optical flow
# Or cv2.TrackerKCF / cv2.TrackerCSRT
# More robust to appearance changes
```

**Pros**: Handles rotation/scale, more robust
**Cons**: Higher computational load

#### Option D: Deep Learning (Advanced)

```python
# Use TensorFlow Lite or ONNX Runtime
# MobileNet SSD or YOLO-tiny for object detection
# Classes: person, cat, dog, car, etc.
```

**Pros**: Semantic understanding, robust
**Cons**: Requires model files, slower inference

**Recommended Approach**: Hybrid

- Start with feature-based tracking (Option C)
- Optional: Add TF Lite for object classification
- Fallback to color tracking if features lost

### 2.3 Object Tracking Implementation

**Core Algorithm**:

```python
class ObjectTracker:
    def __init__(self):
        self.tracker = None
        self.tracking_method = 'KCF'  # or 'CSRT', 'MOSSE'
        self.last_bbox = None
        self.last_position = None
        self.tracking_confidence = 0.0

    def initialize_tracker(self, frame, bbox):
        """Initialize tracker with bounding box"""
        self.tracker = cv2.TrackerKCF_create()
        self.tracker.init(frame, bbox)
        self.last_bbox = bbox

    def update(self, frame):
        """Update tracker with new frame"""
        success, bbox = self.tracker.update(frame)
        if success:
            self.last_bbox = bbox
            self.tracking_confidence = self.calculate_confidence(frame, bbox)
        return success, bbox

    def calculate_confidence(self, frame, bbox):
        """Estimate tracking quality"""
        # Analyze feature richness, template correlation, etc.
        pass
```

**Tracking States**:

1. **ACQUIRING**: User selecting object
2. **TRACKING**: Successfully following object
3. **SEARCHING**: Object lost, attempting re-acquisition
4. **LOST**: Object not found, returning to last position
5. **WAITING**: At last known position, waiting for input

### 2.4 Distance Estimation & Safe Following

### Method 1: Bounding Box Size (Simple)

```python
def estimate_distance(bbox_height):
    """Estimate distance based on object size in frame"""
    # Assumes known object height
    # Distance ∝ 1 / bbox_height

    # Calibration: measure real distance vs bbox size
    reference_height = 200  # pixels at 1 meter
    reference_distance = 1.0  # meters

    estimated_distance = (reference_height * reference_distance) / bbox_height
    return estimated_distance
```

### Method 2: Stereo Vision (If dual cameras available)

- Not applicable to current hardware

### Method 3: Depth from Motion (Monocular)

```python
def estimate_depth_from_motion():
    """Estimate depth using optical flow"""
    # Compare object motion vs robot motion
    # Requires IMU or wheel encoder data
    pass
```

**Safe Following Logic**:

```python
TARGET_DISTANCE = 1.5  # meters
SAFE_MIN_DISTANCE = 0.5  # meters
SAFE_MAX_DISTANCE = 3.0  # meters

def calculate_follow_speed(current_distance, object_velocity):
    """PID controller for maintaining distance"""

    distance_error = current_distance - TARGET_DISTANCE

    # PID gains
    Kp = 0.5
    Ki = 0.1
    Kd = 0.2

    # Speed adjustment
    speed_adjustment = -(Kp * distance_error + Ki * integral + Kd * derivative)

    # Match object velocity
    base_speed = object_velocity

    # Combined control
    follow_speed = base_speed + speed_adjustment

    # Safety limits
    if current_distance < SAFE_MIN_DISTANCE:
        follow_speed = max(follow_speed, -0.3)  # Back up slowly
    elif current_distance > SAFE_MAX_DISTANCE:
        follow_speed = min(follow_speed, 0.8)  # Speed up carefully

    return follow_speed
```

**Steering Control**:

```python
def calculate_steering(bbox_center_x, frame_width):
    """Keep object centered in frame"""

    frame_center_x = frame_width / 2
    error = bbox_center_x - frame_center_x

    # Normalize to -1.0 to 1.0
    steering = error / (frame_width / 2)

    # Apply steering gain
    steering *= STEERING_GAIN

    # Clip to limits
    steering = max(-1.0, min(1.0, steering))

    return steering
```

### 2.5 Object Velocity Estimation

**Optical Flow Method**:

```python
def estimate_object_velocity(prev_bbox, current_bbox, time_delta):
    """Estimate object velocity from position changes"""

    prev_center = get_bbox_center(prev_bbox)
    current_center = get_bbox_center(current_bbox)

    # Pixel displacement
    dx = current_center[0] - prev_center[0]
    dy = current_center[1] - prev_center[1]

    # Convert to real-world velocity (requires calibration)
    # This is simplified - needs camera calibration
    pixel_to_meter = 0.005  # Example conversion factor

    velocity_x = dx * pixel_to_meter / time_delta
    velocity_y = dy * pixel_to_meter / time_delta

    # Forward velocity (assuming camera looks forward)
    forward_velocity = velocity_y

    return forward_velocity
```

---

## Phase 3: Re-acquisition Algorithm

### 3.1 Object Loss Detection

**Triggers**:

- Tracker reports failure
- Tracking confidence below threshold (e.g., 0.3)
- Bounding box moves out of frame
- Object size changes dramatically (occlusion)

### 3.2 Search Strategy

### Stage 1: Local Search (0-5 seconds)

```python
def local_search():
    """Search in last known direction"""

    # Stop movement
    stop_motors()

    # Scan by rotating in place
    rotation_speed = 0.3
    rotation_direction = last_known_direction

    for angle in range(0, 60, 10):  # Scan ±30 degrees
        rotate(rotation_direction, rotation_speed, duration=0.5)
        time.sleep(0.5)

        # Check each frame for object
        if detect_object():
            return OBJECT_FOUND

    return OBJECT_NOT_FOUND
```

### Stage 2: Expanded Search (5-15 seconds)

```python
def expanded_search():
    """Wider rotation search"""

    # 360-degree scan
    for angle in range(0, 360, 20):
        rotate(rotation_direction, rotation_speed, duration=0.5)
        time.sleep(0.5)

        if detect_object():
            return OBJECT_FOUND

    return OBJECT_NOT_FOUND
```

### Stage 3: Return to Last Position (15+ seconds)

```python
def return_to_last_position():
    """Navigate back to position where object was lost"""

    # Store position when tracking starts (using wheel encoders or dead reckoning)
    last_good_position = get_position_when_lost()
    current_position = get_current_position()

    # Calculate path back
    distance = calculate_distance(current_position, last_good_position)
    heading = calculate_heading(current_position, last_good_position)

    # Navigate back (simplified - assumes open path)
    rotate_to_heading(heading)
    drive_distance(distance)

    # Orient to same heading as when object was lost
    rotate_to_heading(last_good_heading)

    # Enter WAITING state
    state = WAITING
```

### 3.3 Position Tracking (Odometry)

### Method 1: Dead Reckoning (Basic)

```python
class Odometry:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = time.time()

    def update(self, left_speed, right_speed):
        """Update position based on differential drive model"""

        current_time = time.time()
        dt = current_time - self.last_time

        # Wheelbase and wheel radius (to be measured)
        WHEELBASE = 0.15  # meters
        WHEEL_RADIUS = 0.05  # meters

        # Calculate velocities
        v_left = left_speed * WHEEL_RADIUS
        v_right = right_speed * WHEEL_RADIUS

        # Differential drive kinematics
        v = (v_left + v_right) / 2.0
        omega = (v_right - v_left) / WHEELBASE

        # Update pose
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta += omega * dt

        self.last_time = current_time

    def get_position(self):
        return (self.x, self.y, self.theta)

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
```

### Method 2: IMU Integration (If Available)

- Use gyroscope for heading
- Use accelerometer for movement (double integration)
- Requires sensor fusion (Kalman filter)

### 3.4 Re-acquisition State Machine

```python
class ReacquisitionStateMachine:
    STATES = ['TRACKING', 'LOCAL_SEARCH', 'EXPANDED_SEARCH', 'RETURNING', 'WAITING']

    def __init__(self):
        self.state = 'TRACKING'
        self.time_lost = 0
        self.search_attempts = 0

    def update(self, tracking_success):
        if tracking_success:
            self.state = 'TRACKING'
            self.time_lost = 0
            self.search_attempts = 0

        else:
            time_since_lost = time.time() - self.time_lost

            if self.time_lost == 0:
                self.time_lost = time.time()

            if time_since_lost < 5:
                self.state = 'LOCAL_SEARCH'
                self.local_search()

            elif time_since_lost < 15:
                self.state = 'EXPANDED_SEARCH'
                self.expanded_search()

            else:
                self.state = 'RETURNING'
                self.return_to_last_position()
                self.state = 'WAITING'
```

---

## Phase 4: Inverted Operation Handling

### 4.1 Orientation Detection

### Method 1: Accelerometer (Recommended)

```python
# Use MPU6050 or similar IMU connected via I2C

import smbus

class OrientationDetector:
    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.address = 0x68  # MPU6050 default
        self.initialize_imu()

    def initialize_imu(self):
        # Wake up MPU6050
        self.bus.write_byte_data(self.address, 0x6B, 0)

    def read_accel(self):
        # Read accelerometer data
        accel_x = self.read_word(0x3B)
        accel_y = self.read_word(0x3D)
        accel_z = self.read_word(0x3F)

        return (accel_x, accel_y, accel_z)

    def is_inverted(self):
        accel_x, accel_y, accel_z = self.read_accel()

        # If Z-axis is negative, robot is upside down
        # (Assumes Z-axis points up when right-side up)
        return accel_z < 0
```

### Method 2: Image Analysis (Fallback)

```python
def detect_inversion_from_image(frame):
    """Detect if camera is upside down based on image features"""

    # Assume horizon or ground plane is visible
    # Detect horizon line orientation
    # If horizon is inverted, robot is upside down

    # This is complex and unreliable - prefer IMU
    pass
```

**Method 3: Manual Toggle (Simple)**

```python
# Add button to web interface
# User manually indicates inversion
```

### 4.2 Motor Control Inversion

**Implementation**:

```python
class InvertedDriveController:
    def __init__(self, thunderborg):
        self.tb = thunderborg
        self.is_inverted = False
        self.orientation_detector = OrientationDetector()

    def update_orientation(self):
        """Check orientation and update inversion state"""
        self.is_inverted = self.orientation_detector.is_inverted()

    def set_motors(self, left_speed, right_speed):
        """Set motor speeds with inversion handling"""

        if self.is_inverted:
            # When inverted:
            # - Forward becomes backward (reverse speed sign)
            # - Left motor becomes right motor (swap sides)
            # - Right motor becomes left motor (swap sides)

            inverted_left = -right_speed
            inverted_right = -left_speed

            self.tb.SetMotor1(inverted_right)
            self.tb.SetMotor2(inverted_left)
        else:
            # Normal operation
            self.tb.SetMotor1(right_speed)
            self.tb.SetMotor2(left_speed)

    def get_orientation_status(self):
        return "INVERTED" if self.is_inverted else "NORMAL"
```

### 4.3 Camera Orientation Adjustment

**Auto-Flip Camera Image**:

```python
def process_frame(frame, is_inverted):
    """Flip frame if robot is inverted"""

    if is_inverted:
        # Rotate 180 degrees
        frame = cv2.rotate(frame, cv2.ROTATE_180)

    return frame
```

### 4.4 Tracking Continuity During Flip

**Challenge**: Object tracking may fail during flip transition

**Solution**:

```python
def handle_flip_transition():
    """Maintain tracking through orientation change"""

    # Detect orientation change
    if orientation_changed():
        # Pause tracking briefly
        pause_tracking()

        # Wait for stabilization (0.5-1 second)
        time.sleep(0.5)

        # Re-initialize tracker with flipped image
        reinitialize_tracker()

        # Resume tracking
        resume_tracking()
```

---

## Phase 5: Integration & Mode Selection

### 5.1 Unified Control System

**Create**: `MonsterController.py` - Main controller integrating all modes

**Modes**:

1. **MANUAL**: Web interface control (existing)
2. **LINE_FOLLOW**: Track following (existing)
3. **OBJECT_FOLLOW**: Object tracking (new)
4. **IDLE**: Stopped, awaiting command

**Mode Switching**:

```python
class MonsterController:
    def __init__(self):
        self.mode = 'IDLE'
        self.thunderborg = ThunderBorg.ThunderBorg()
        self.thunderborg.Init()

        # Controllers
        self.manual_controller = ManualController(self.thunderborg)
        self.line_follower = LineFollower(self.thunderborg)
        self.object_tracker = ObjectFollower(self.thunderborg)

        # Web interface
        self.web_server = WebServer(self)

    def set_mode(self, new_mode):
        # Stop current mode
        self.stop_all()

        # Switch mode
        self.mode = new_mode

        # Start new mode
        if new_mode == 'MANUAL':
            self.manual_controller.start()
        elif new_mode == 'LINE_FOLLOW':
            self.line_follower.start()
        elif new_mode == 'OBJECT_FOLLOW':
            self.object_tracker.start()

    def stop_all(self):
        self.manual_controller.stop()
        self.line_follower.stop()
        self.object_tracker.stop()
        self.thunderborg.MotorsOff()
```

### 5.2 Web Interface Updates

**Add Mode Selector**:

```html
<select id="mode-selector">
    <option value="IDLE">Idle</option>
    <option value="MANUAL">Manual Control</option>
    <option value="LINE_FOLLOW">Line Following</option>
    <option value="OBJECT_FOLLOW">Object Tracking</option>
</select>
```

**Object Selection Interface**:

```html
<!-- For object tracking mode -->
<div id="object-selector">
    <h3>Select Object to Track</h3>
    <button id="capture-template">Tap Object on Screen</button>
    <canvas id="selection-canvas"></canvas>
</div>
```

**JavaScript for Object Selection**:

```javascript
// Allow user to tap on video stream to select object
videoElement.addEventListener('click', function(event) {
    const rect = videoElement.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Send coordinates to server
    fetch(`/select_object?x=${x}&y=${y}`)
        .then(response => response.json())
        .then(data => {
            // Show selected object bounding box
            drawBoundingBox(data.bbox);
        });
});
```

### 5.3 Real-time Telemetry

**Data to Display**:

- Current mode
- Object tracking status
- Distance to object
- Battery voltage
- Orientation (normal/inverted)
- Speed (current)
- Connection status

**WebSocket Telemetry**:

```python
def send_telemetry(websocket):
    """Send real-time data to web interface"""

    telemetry = {
        'mode': controller.mode,
        'tracking_status': tracker.state,
        'distance': tracker.estimated_distance,
        'battery': thunderborg.GetBatteryReading(),
        'orientation': drive_controller.get_orientation_status(),
        'speed': current_speed,
        'timestamp': time.time()
    }

    websocket.send(json.dumps(telemetry))
```

---

## Phase 6: Hardware Requirements & Dependencies

### 6.1 Required Hardware

- Raspberry Pi 3B (existing)
- Pi Camera Module (existing)
- ThunderBorg Motor Controller (existing)
- MonsterBorg Chassis (existing)

### 6.2 Optional Hardware

- **IMU Module (Recommended)**: MPU6050 or BNO055
  - Purpose: Orientation detection, improved odometry
  - Connection: I2C
  - Cost: ~$5-10

- **Ultrasonic Sensor** (Optional): HC-SR04
  - Purpose: Backup distance measurement
  - Connection: GPIO
  - Cost: ~$2

- **Wheel Encoders** (Optional)
  - Purpose: Accurate odometry
  - Connection: GPIO (interrupt pins)
  - Cost: ~$10

### 6.3 Software Dependencies

**Python Libraries**:

```bash
# Core dependencies (already installed)
pip3 install opencv-python
pip3 install numpy
pip3 install picamera

# New dependencies
pip3 install websockets        # WebSocket server
pip3 install smbus            # I2C communication (usually pre-installed)

# Optional (for deep learning)
pip3 install tensorflow-lite  # TensorFlow Lite for object detection
pip3 install onnxruntime      # ONNX Runtime (alternative)
```

**System Packages**:

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-opencv \
    python3-numpy \
    python3-picamera \
    i2c-tools \
    libatlas-base-dev
```

**Camera Module**:

```bash
# Enable camera and I2C
sudo raspi-config
# Enable: Camera, I2C

# Load camera driver
sudo modprobe bcm2835-v4l2
```

---

## Phase 7: Implementation Roadmap

### Sprint 1: Mobile Web Interface (Week 1)

- [ ] Update HTML/CSS for responsive design
- [ ] Implement touch controls
- [ ] Add virtual joystick
- [ ] Test on multiple mobile devices (iOS Safari, Android Chrome)
- [ ] Optimize camera streaming for mobile bandwidth

### Sprint 2: Object Detection Foundation (Week 2)

- [ ] Implement feature-based tracker (KCF/CSRT)
- [ ] Create object selection interface
- [ ] Add template matching fallback
- [ ] Test tracking performance on Pi 3B
- [ ] Optimize for 30 fps operation

### Sprint 3: Distance & Following (Week 3)

- [ ] Implement distance estimation
- [ ] Create following PID controller
- [ ] Add safe distance limits
- [ ] Test with different objects (person, ball, toy car)
- [ ] Tune PID parameters

### Sprint 4: Re-acquisition System (Week 4)

- [ ] Implement odometry system
- [ ] Create search state machine
- [ ] Add return-to-position logic
- [ ] Test re-acquisition reliability
- [ ] Add timeout and safety limits

### Sprint 5: Inversion Handling (Week 5)

- [ ] Source and install IMU module (MPU6050)
- [ ] Implement orientation detection
- [ ] Create inverted motor controller
- [ ] Test flip transitions
- [ ] Add auto-recovery logic

### Sprint 6: Integration & Testing (Week 6)

- [ ] Create unified MonsterController
- [ ] Integrate all modes
- [ ] Add mode switching interface
- [ ] Full system testing
- [ ] Performance optimization
- [ ] Documentation

---

## Phase 8: Testing Strategy

### 8.1 Unit Tests

- Object tracker initialization and update
- Distance estimation accuracy
- Motor inversion logic
- Odometry calculations
- Search algorithms

### 8.2 Integration Tests

- Mode switching
- Web interface communication
- Camera stream reliability
- Motor control responsiveness
- Inversion detection

### 8.3 Field Tests

1. **Object Following**:
   - Person walking at various speeds
   - Small object (ball, toy)
   - Another robot
   - Different lighting conditions

2. **Re-acquisition**:
   - Object goes behind obstacle
   - Object moves out of frame quickly
   - Multiple similar objects
   - Return-to-position accuracy

3. **Inversion**:
   - Manual flip test
   - Ramp flip test
   - Tracking continuity during flip
   - Motor control correctness

4. **Mobile Interface**:
   - iOS Safari
   - Android Chrome
   - Various screen sizes
   - Different network conditions
   - Touch responsiveness

---

## Phase 9: Configuration Files

### 9.1 Update Settings.py

```python
# Object Tracking Settings
objectTrackingEnabled = True
trackingMethod = 'KCF'  # Options: 'KCF', 'CSRT', 'MOSSE', 'TEMPLATE'
targetDistance = 1.5  # meters
safeMinDistance = 0.5  # meters
safeMaxDistance = 3.0  # meters

# Re-acquisition Settings
localSearchTime = 5  # seconds
expandedSearchTime = 15  # seconds
searchRotationSpeed = 0.3
returnToPositionEnabled = True

# Inversion Settings
inversionDetectionEnabled = True
inversionMethod = 'IMU'  # Options: 'IMU', 'MANUAL', 'IMAGE'
imuAddress = 0x68  # MPU6050 I2C address
autoFlipCameraEnabled = True

# Web Interface Settings
websocketEnabled = True
websocketPort = 8081
telemetryUpdateRate = 10  # Hz

# Following PID Gains
followDistanceP = 0.5
followDistanceI = 0.1
followDistanceD = 0.2

followSteeringP = 0.8
followSteeringI = 0.05
followSteeringD = 0.3

# Safety Settings
maxFollowSpeed = 0.8
emergencyStopDistance = 0.3  # meters
trackingTimeoutDuration = 30  # seconds
```

---

## Phase 10: Safety Considerations

### 10.1 Collision Avoidance

- Minimum distance enforcement (0.5m)
- Emergency stop on tracking loss + close proximity
- Ultrasonic sensor backup (optional)
- Speed limits based on distance

### 10.2 Battery Management

- Low battery detection (< 7V)
- Automatic shutdown at critical level
- Battery level display on interface
- Speed reduction at low battery

### 10.3 Timeout & Failsafes

- Tracking timeout (30 seconds)
- Web connection watchdog
- Automatic mode switch to IDLE on timeout
- Motor auto-stop on exception

### 10.4 User Control

- Emergency stop button (always accessible)
- Manual override from any mode
- Clear mode indicators
- Confirmation for autonomous modes

---

## Phase 11: Performance Optimization

### 11.1 Raspberry Pi 3B Constraints

- CPU: 4-core ARM Cortex-A53 @ 1.2GHz
- RAM: 1GB
- Limited processing power

### 11.2 Optimization Strategies

**Image Processing**:

- Reduce resolution (320x240 or 160x120 for tracking)
- Use grayscale for feature detection
- Limit processing threads (2-3)
- Skip frames if processing lags (process every 2nd frame)

**Tracking Algorithm**:

- Use KCF (fastest) over CSRT (more accurate but slower)
- Limit search region to predicted area
- Use template matching for re-acquisition (faster)

**Python Optimization**:

```python
# Use NumPy vectorized operations
# Avoid Python loops where possible
# Pre-allocate arrays
# Use in-place operations
```

**Multi-threading**:

- Separate threads for:
  - Camera capture
  - Image processing
  - Motor control
  - Web communication
- Use queues for thread communication
- Avoid GIL contention

---

## Phase 12: Advanced Features (Future)

### 12.1 Machine Learning Object Detection

- TensorFlow Lite MobileNet SSD
- Detect and classify objects (person, car, pet)
- Pre-trained model on COCO dataset
- ~5-10 fps on RPi 3B

### 12.2 Gesture Recognition

- Detect hand gestures from tracking target
- Stop/Go/Left/Right commands
- OpenCV contour analysis or MediaPipe

### 12.3 Multi-Object Tracking

- Track multiple objects simultaneously
- User selects priority target
- Switch targets on command

### 12.4 Path Planning

- Obstacle avoidance
- Predicted path of target
- Optimal following path

### 12.5 Cloud Integration

- Remote monitoring via cloud service
- Video streaming to phone app
- GPS tracking (with GPS module)
- Data logging and analytics

---

## Summary

This implementation plan provides a comprehensive roadmap for upgrading the MonsterBorg to include:

1. ✅ Mobile-optimized web controls with touch interface
2. ✅ Intelligent object tracking using OpenCV
3. ✅ Distance estimation and safe following
4. ✅ Re-acquisition algorithm with return-to-position
5. ✅ Inverted operation handling with IMU
6. ✅ Unified control system with mode selection

The plan is broken into manageable sprints, with clear testing criteria and safety considerations. The implementation leverages existing code where possible and introduces new modular components that integrate cleanly with the current architecture.

**Estimated Timeline**: 6-8 weeks for full implementation
**Difficulty**: Intermediate to Advanced
**Hardware Cost**: ~$10-20 (optional IMU module)

Next steps: Begin with Sprint 1 (Mobile Web Interface) and progressively add features while maintaining a stable, testable system at each stage.
