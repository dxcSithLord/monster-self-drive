# MonsterBorg Self-Drive Project Constitution

**Version**: 1.0
**Effective Date**: 2025-11-14
**Project**: MonsterBorg Self-Drive System
**Repository**: <https://github.com/dxcSithLord/monster-self-drive>

---

## Table of Contents

1. [Preamble](#preamble)
2. [Core Principles](#core-principles)
3. [Development Standards](#development-standards)
4. [Code Organization](#code-organization)
5. [Design Philosophy](#design-philosophy)
6. [Safety and Ethics](#safety-and-ethics)
7. [Contribution Guidelines](#contribution-guidelines)
8. [Testing and Quality Assurance](#testing-and-quality-assurance)
9. [Documentation Standards](#documentation-standards)
10. [Version Control Practices](#version-control-practices)
11. [Release Management](#release-management)
12. [Governance](#governance)
13. [Amendment Process](#amendment-process)

---

## Preamble

This constitution establishes the foundational principles, standards, and
practices for the MonsterBorg Self-Drive Project. It serves as a living
document to guide all contributors in maintaining code quality, ensuring
safety, and fostering a collaborative development environment.

### Project Mission

To create an open-source, educational robotics platform that demonstrates:

- Autonomous navigation and object tracking
- Mobile-first web interfaces
- Real-time computer vision processing
- Safe and reliable robot control
- Best practices in embedded Python development

### Project Vision

Empower hobbyists, students, and robotics enthusiasts to learn and experiment
with autonomous systems through accessible, well-documented, and
production-quality code.

### Project Values

1. **Safety First**: Robot operation must never endanger people, animals, or property
2. **Educational Focus**: Code should be readable, well-commented, and instructive
3. **Robustness**: Systems should handle errors gracefully and recover when possible
4. **Accessibility**: Interfaces should be usable by everyone, regardless of
   device or ability
5. **Open Collaboration**: Welcome contributions from all skill levels
6. **Performance Awareness**: Optimize for constrained hardware (Raspberry Pi 3B)

---

## Core Principles

### 1. Safety Above All

**Principle**: The safety of users, bystanders, and property is the highest priority.

**Implementation**:

- Emergency stop functionality must be accessible at all times
- Motors must stop immediately on connection loss
- Collision avoidance is mandatory, not optional
- Battery protection prevents damage and fire hazards
- All autonomous behaviors must have failsafes

**Code Requirements**:

```python
# Example: Every motor control function must include timeout
def set_motors(left_speed, right_speed, timeout=2.0):
    """
    Set motor speeds with mandatory timeout failsafe.

    Args:
        left_speed: Speed for left motors (-1.0 to 1.0)
        right_speed: Speed for right motors (-1.0 to 1.0)
        timeout: Maximum time in seconds before auto-stop
    """
    # Implementation must include watchdog timer
    pass
```

### 2. Readability Over Cleverness

**Principle**: Code should be obvious and maintainable, not compact or clever.

**Example**:

```python
# GOOD: Clear and explicit
def calculate_distance_from_bbox(bbox_height, reference_height, reference_distance):
    """Calculate distance using similar triangles principle."""
    if bbox_height <= 0:
        return None
    estimated_distance = (reference_height * reference_distance) / bbox_height
    return estimated_distance

# BAD: Clever but unclear
def dist(h): return RH*RD/h if h>0 else None
```

### 3. Fail Safely, Recover Gracefully

**Principle**: When errors occur, default to safe state (motors off) and
attempt recovery.

**Pattern**:

```python
def critical_operation():
    try:
        # Attempt operation
        result = perform_action()
    except CommunicationError as e:
        # Log error
        logger.error(f"Communication failed: {e}")
        # Safe state
        motors_off()
        # Attempt recovery
        if can_recover():
            reconnect()
        else:
            # Notify user
            raise SafetyException("Manual intervention required")
    return result
```

### 4. Design for Testability

**Principle**: Code should be structured to enable automated testing.

**Practices**:

- Dependency injection (pass dependencies as parameters)
- Pure functions where possible (no side effects)
- Mockable hardware interfaces
- Separate business logic from I/O

**Example**:

```python
# GOOD: Testable design
class ObjectTracker:
    def __init__(self, camera_interface, motor_controller):
        self.camera = camera_interface
        self.motors = motor_controller

    def update(self, frame):
        # Pure computation - easily testable
        bbox = self.detect_object(frame)
        return bbox

# BAD: Hard to test
class ObjectTracker:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)  # Hardware coupling
        self.motors = ThunderBorg.ThunderBorg()  # Direct dependency
```

### 5. Performance Pragmatism

**Principle**: Optimize where it matters, prioritize clarity elsewhere.

**Guidelines**:

- Profile before optimizing (use `cProfile`, `line_profiler`)
- Optimize hot paths (image processing, control loops)
- Accept slower code for infrequent operations (setup, configuration)
- Document why optimizations are necessary

**Example**:

```python
# Hot path: Called 30 times per second
def process_frame_fast(frame):
    """Optimized for speed - called at 30 Hz."""
    # Use NumPy vectorized operations
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Downscale for performance
    small = cv2.resize(gray, (160, 120))
    return small

# Cold path: Called once at startup
def load_configuration(filepath):
    """Clarity prioritized - called once at startup."""
    with open(filepath, 'r') as f:
        config = json.load(f)
    # Validate each field explicitly
    if 'target_distance' not in config:
        raise ValueError("Missing required field: target_distance")
    # More validation...
    return config
```

### 6. Documentation Is Code

**Principle**: Documentation is as important as implementation.

**Requirements**:

- Every public function/class has a docstring
- Complex algorithms have inline comments
- README explains setup and usage
- Architecture decisions are documented (ADRs)

### 7. Backwards Compatibility

**Principle**: Breaking changes require major version bump and migration guide.

**Rules**:

- Deprecate before removing (minimum 1 minor version)
- Provide migration scripts where possible
- Document breaking changes in CHANGELOG
- Support configuration file updates

---

## Development Standards

### Programming Language

**Primary**: Python 3.11+
**Target**: Python 3.12 (recommended for development)
**Compatibility**: Must run on Python 3.11 (Raspberry Pi OS Bookworm)

**Rationale**: Python 3.11 is the current stable version on Raspberry Pi OS.
Python 3.12 offers performance improvements and better typing support for
development.

### Code Style

**Standard**: PEP 8 (enforced via `black` and `flake8`)

**Formatter**: Black (line length: 100)

```bash
black --line-length 100 .
```

**Linter**: Flake8

```bash
flake8 --max-line-length 100 --extend-ignore E203,W503
```

**Type Checking**: MyPy (enforced for new code)

```bash
mypy --strict .
```

### Naming Conventions

**Modules**: `lowercase_with_underscores.py`

```python
# GOOD
object_tracker.py
distance_estimator.py

# BAD
ObjectTracker.py
distanceEstimator.py
```

**Classes**: `PascalCase`

```python
class ObjectTracker:
    pass

class ReacquisitionStateMachine:
    pass
```

**Functions/Methods**: `lowercase_with_underscores`

```python
def calculate_distance(bbox):
    pass

def estimate_velocity(prev_pos, current_pos, time_delta):
    pass
```

**Constants**: `UPPERCASE_WITH_UNDERSCORES`

```python
TARGET_DISTANCE = 1.5  # meters
SAFE_MIN_DISTANCE = 0.5  # meters
MAX_TRACKING_TIMEOUT = 30  # seconds
```

**Private Members**: `_leading_underscore`

```python
class Tracker:
    def __init__(self):
        self._internal_state = {}

    def _helper_method(self):
        pass
```

### Type Hints

**Requirement**: All new code must use type hints

**Example**:

```python
from typing import Optional, Tuple, List
import numpy as np

def calculate_distance(
    bbox_height: int,
    reference_height: int,
    reference_distance: float
) -> Optional[float]:
    """
    Calculate distance to object using bounding box height.

    Args:
        bbox_height: Height of bounding box in pixels
        reference_height: Reference height in pixels at known distance
        reference_distance: Known distance in meters

    Returns:
        Estimated distance in meters, or None if calculation invalid
    """
    if bbox_height <= 0:
        return None
    return (reference_height * reference_distance) / bbox_height

def detect_objects(frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect objects in frame.

    Args:
        frame: Input image (BGR format)

    Returns:
        List of bounding boxes (x, y, width, height)
    """
    # Implementation
    return []
```

### Docstring Format

**Standard**: Google Style

**Template**:

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief description (one line).

    Longer description if needed. Explain what the function does,
    why it exists, and any important context.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ErrorType: When and why this error is raised

    Example:
        >>> result = function_name(value1, value2)
        >>> print(result)
        Expected output

    Note:
        Any additional information, warnings, or caveats
    """
    # Implementation
    pass
```

### Import Organization

**Order**:

1. Standard library imports
2. Third-party imports
3. Local application imports

**Format**: Sorted alphabetically within each group

**Example**:

```python
# Standard library
import math
import time
from typing import Optional, Tuple

# Third-party
import cv2
import numpy as np

# Local
import Settings
from object_tracker import ObjectTracker
from motor_controller import MotorController
```

**Tool**: `isort` (compatible with Black)

```bash
isort --profile black .
```

---

## Code Organization

### Directory Structure

```text
monster-self-drive/
├── README.md                  # Project overview and quick start
├── REQUIREMENTS.md            # Detailed requirements specification
├── PROJECT_CONSTITUTION.md    # This document
├── IMPLEMENTATION_PLAN.md     # Implementation roadmap
├── LICENSE                    # License file (specify open-source license)
├── CHANGELOG.md               # Version history
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup (if distributing)
├── .gitignore                 # Git ignore rules
├── .flake8                    # Flake8 configuration
├── mypy.ini                   # MyPy configuration
├── pytest.ini                 # Pytest configuration
│
├── src/                       # Source code (new structure)
│   ├── __init__.py
│   ├── web/                   # Web interface
│   │   ├── __init__.py
│   │   ├── server.py          # Web server (refactored monsterWeb.py)
│   │   ├── websocket.py       # WebSocket handler
│   │   └── static/            # Static files (HTML, CSS, JS)
│   │       ├── index.html
│   │       ├── styles.css
│   │       └── app.js
│   ├── vision/                # Computer vision
│   │   ├── __init__.py
│   │   ├── camera.py          # Camera interface
│   │   ├── image_processor.py # Image processing (refactored)
│   │   ├── object_tracker.py  # Object tracking (new)
│   │   └── distance_estimator.py  # Distance estimation (new)
│   ├── control/               # Motor control and navigation
│   │   ├── __init__.py
│   │   ├── motor_controller.py    # ThunderBorg interface
│   │   ├── inverted_controller.py # Inversion handling (new)
│   │   ├── odometry.py            # Position tracking (new)
│   │   └── pid_controller.py      # PID implementation
│   ├── navigation/            # High-level navigation
│   │   ├── __init__.py
│   │   ├── line_follower.py   # Line following mode
│   │   ├── object_follower.py # Object following mode (new)
│   │   └── reacquisition.py   # Re-acquisition algorithm (new)
│   ├── sensors/               # Sensor interfaces
│   │   ├── __init__.py
│   │   ├── imu.py             # IMU interface (new)
│   │   └── ultrasonic.py      # Ultrasonic sensor (optional)
│   ├── utils/                 # Utilities
│   │   ├── __init__.py
│   │   ├── logger.py          # Logging configuration
│   │   ├── config.py          # Configuration management
│   │   └── safety.py          # Safety utilities (watchdog, etc.)
│   └── main.py                # Main entry point
│
├── legacy/                    # Original code (preserved for reference)
│   ├── monsterWeb.py
│   ├── MonsterAuto.py
│   ├── ImageProcessor.py
│   ├── ThunderBorg.py
│   └── Settings.py
│
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── unit/                  # Unit tests
│   │   ├── test_object_tracker.py
│   │   ├── test_distance_estimator.py
│   │   └── test_pid_controller.py
│   ├── integration/           # Integration tests
│   │   ├── test_tracking_pipeline.py
│   │   └── test_web_interface.py
│   └── fixtures/              # Test data
│       ├── test_images/
│       └── test_configs/
│
├── docs/                      # Documentation
│   ├── architecture.md        # System architecture
│   ├── user_manual.md         # User guide
│   ├── installation.md        # Installation instructions
│   ├── troubleshooting.md     # Common issues and solutions
│   ├── api/                   # API documentation (Sphinx)
│   └── images/                # Diagrams and screenshots
│
├── config/                    # Configuration files
│   ├── default.json           # Default configuration
│   ├── development.json       # Development overrides
│   └── calibration.json       # Calibration data
│
├── scripts/                   # Utility scripts
│   ├── install_raspberry_pi.sh    # Pi installation script
│   ├── calibrate_distance.py      # Distance calibration tool
│   ├── calibrate_odometry.py      # Odometry calibration tool
│   └── update_system.sh           # Update script
│
└── logs/                      # Log files (gitignored)
    └── .gitkeep
```

### Module Responsibilities

**Principle**: Single Responsibility - each module has one clear purpose

|Module|Responsibility|
|------|----------------|
|`web/server.py`|HTTP/WebSocket server, request routing|
|`web/websocket.py`|Real-time communication with clients|
|`vision/camera.py`|Camera initialization, frame capture|
|`vision/image_processor.py`|Image processing pipeline|
|`vision/object_tracker.py`|Object detection and tracking|
|`vision/distance_estimator.py`|Distance calculation from visual cues|
|`control/motor_controller.py`|Low-level motor commands (ThunderBorg)|
|`control/inverted_controller.py`|Orientation detection, motor inversion|
|`control/odometry.py`|Position/heading estimation|
|`control/pid_controller.py`|PID control implementation|
|`navigation/line_follower.py`|Line-following behavior|
|`navigation/object_follower.py`|Object-following behavior|
|`navigation/reacquisition.py`|Object search and recovery|
|`sensors/imu.py`|IMU data acquisition|
|`utils/logger.py`|Logging setup and utilities|
|`utils/config.py`|Configuration loading/saving|
|`utils/safety.py`|Safety checks and failsafes|
|`main.py`|Application entry point, mode coordination|

---

## Design Philosophy

### Modularity and Separation of Concerns

**Pattern**: Layered Architecture

```text
┌─────────────────────────────────────┐
│  User Interface Layer               │  (Web, CLI)
├─────────────────────────────────────┤
│  Navigation Layer                   │  (Line Follow, Object Follow)
├─────────────────────────────────────┤
│  Control Layer                      │  (PID, Motor Control, Odometry)
├─────────────────────────────────────┤
│  Vision Layer                       │  (Camera, Tracking, Detection)
├─────────────────────────────────────┤
│  Hardware Abstraction Layer         │  (ThunderBorg, IMU, Sensors)
└─────────────────────────────────────┘
```

**Rules**:

- Upper layers depend on lower layers (not vice versa)
- Each layer has well-defined interfaces
- Hardware details hidden behind abstractions
- Business logic independent of I/O

### Dependency Injection

**Principle**: Pass dependencies rather than creating them internally

**Example**:

```python
# GOOD: Dependencies injected
class ObjectFollower:
    def __init__(
        self,
        tracker: ObjectTracker,
        distance_estimator: DistanceEstimator,
        motor_controller: MotorController,
        config: dict
    ):
        self.tracker = tracker
        self.estimator = distance_estimator
        self.motors = motor_controller
        self.config = config

# Usage (allows mocking for tests)
tracker = ObjectTracker()
estimator = DistanceEstimator()
motors = MotorController()
follower = ObjectFollower(tracker, estimator, motors, config)

# BAD: Dependencies created internally
class ObjectFollower:
    def __init__(self):
        self.tracker = ObjectTracker()  # Hard dependency
        self.motors = ThunderBorg.ThunderBorg()  # Can't mock for testing
```

### Configuration Over Hard-Coding

**Principle**: All tunable parameters must be configurable

**Pattern**:

```python
# config/default.json
{
    "object_tracking": {
        "algorithm": "KCF",
        "confidence_threshold": 0.3,
        "target_distance": 1.5,
        "safe_min_distance": 0.5,
        "safe_max_distance": 3.0
    },
    "pid": {
        "distance": {
            "P": 0.5,
            "I": 0.1,
            "D": 0.2
        },
        "steering": {
            "P": 0.8,
            "I": 0.05,
            "D": 0.3
        }
    }
}

# Code
from utils.config import load_config

config = load_config('config/default.json')
target_distance = config['object_tracking']['target_distance']
pid_p = config['pid']['distance']['P']
```

### Event-Driven Architecture (where appropriate)

**Use Cases**:

- User input handling
- Mode changes
- Emergency stops
- Object detection events

**Pattern**:

```python
from typing import Callable, Dict, List

class EventBus:
    """Simple event bus for decoupled communication."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type: str, data: dict):
        """Publish event to all subscribers."""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                callback(data)

# Usage
event_bus = EventBus()

# Subscribe
def on_object_detected(data):
    print(f"Object detected at {data['bbox']}")

event_bus.subscribe('object_detected', on_object_detected)

# Publish
event_bus.publish('object_detected', {'bbox': (100, 100, 50, 50)})
```

### Graceful Degradation

**Principle**: System continues to function with reduced features if components fail

**Examples**:

- If IMU unavailable, use manual orientation toggle
- If WebSocket fails, fall back to HTTP polling
- If object tracking fails, allow manual control
- If distance estimation uncertain, use conservative speed

**Implementation**:

```python
def initialize_imu():
    """Initialize IMU with graceful fallback."""
    try:
        imu = IMU()
        logger.info("IMU initialized successfully")
        return imu
    except I2CError:
        logger.warning("IMU not found - using manual orientation mode")
        return None  # System continues without IMU

def get_orientation():
    """Get orientation with fallback."""
    if self.imu is not None:
        return self.imu.is_inverted()
    else:
        # Fallback to manual toggle
        return self.manual_inversion_state
```

---

## Safety and Ethics

### Safety Principles

1. **Fail-Safe Defaults**: When in doubt, stop motors
2. **Defense in Depth**: Multiple layers of safety (software + hardware)
3. **Predictable Behavior**: Robot actions should be obvious to observers
4. **Emergency Override**: User can always take control
5. **Responsible Autonomy**: Autonomous modes supervised and limited

### Safety Checklist (Pre-Release)

Every release must verify:

- [ ] Emergency stop button functional and tested
- [ ] Connection watchdog stops motors within 2 seconds
- [ ] Collision avoidance triggers at safe distance
- [ ] Battery protection prevents over-discharge
- [ ] Thermal monitoring prevents overheating
- [ ] All autonomous modes have timeout limits
- [ ] Speed limits enforced in code
- [ ] Inverted operation tested (motors reverse correctly)
- [ ] Web interface cannot send invalid commands
- [ ] Error states always result in stopped motors

### Ethical Guidelines

1. **Privacy**: No cameras or data collection without user consent
2. **Transparency**: Clearly state when robot is in autonomous mode
3. **Accessibility**: Ensure interface usable by people with disabilities
4. **Open Source**: Share improvements with community
5. **Educational Use**: Prioritize learning over competitive advantage
6. **Environmental Responsibility**: Efficient power usage, no waste

### Responsible Testing

**Rules**:

- Test in controlled environments first (indoor, clear area)
- Use safety tether during initial autonomous tests
- Start with low speeds, increase gradually
- Have manual override ready at all times
- Warn bystanders when testing autonomous modes
- Never test near stairs, water, or fragile objects
- Document all test failures and near-misses

---

## Contribution Guidelines

### Who Can Contribute

Everyone! Contributions welcome from:

- Beginners (documentation, simple fixes)
- Students (features, experiments)
- Experienced developers (architecture, optimization)
- Hardware enthusiasts (sensor integration, mechanical)

### Contribution Process

1. **Fork** the repository
2. **Create branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make changes** following this constitution
4. **Write tests** for new functionality
5. **Update documentation** (README, docstrings, etc.)
6. **Run quality checks** (black, flake8, mypy, pytest)
7. **Commit** with descriptive message
8. **Push** to your fork
9. **Open Pull Request** with description

### Pull Request Requirements

**Must Include**:

- [ ] Description of changes and motivation
- [ ] Tests for new functionality (unit and/or integration)
- [ ] Documentation updates (code and user-facing)
- [ ] CHANGELOG entry (in Unreleased section)
- [ ] No breaking changes (or clearly marked with migration guide)
- [ ] All CI checks passing (linting, tests, type checking)

**Reviewers Will Check**:

- Code quality (readability, style compliance)
- Test coverage (aim for >70%)
- Performance impact (especially on Pi 3B)
- Safety implications
- Documentation clarity

### Commit Message Format

**Standard**: Conventional Commits

**Format**: `<type>(<scope>): <description>`

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring, no behavior change
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, etc.

**Examples**:

```text
feat(tracking): add CSRT tracker as fallback option
fix(motors): correct inverted motor direction calculation
docs(readme): add installation instructions for Ubuntu
refactor(camera): separate capture from processing logic
perf(vision): reduce image resolution for faster processing
test(odometry): add unit tests for position calculation
chore(deps): update OpenCV to 4.9.0
```

### Code Review Guidelines

**Reviewers Should**:

- Be constructive and respectful
- Explain reasoning behind suggestions
- Prioritize safety and correctness
- Consider performance implications
- Check for edge cases
- Verify tests are meaningful

**Authors Should**:

- Respond to all comments
- Not take criticism personally
- Ask questions if unclear
- Iterate based on feedback
- Squash commits before merge (optional)

---

## Testing and Quality Assurance

### Testing Pyramid

```text
        /\
       /  \    10% - End-to-End Tests (field tests)
      /────\
     /      \  20% - Integration Tests (component interaction)
    /────────\
   /          \ 70% - Unit Tests (individual functions/classes)
  /────────────\
```

### Test Coverage Requirements

**Minimum**: 70% overall
**Critical Modules**: 90% (safety, motor control, tracking)

**Tools**:

```bash
pytest --cov=src --cov-report=html
# View coverage report in htmlcov/index.html
```

### Unit Test Standards

**Framework**: pytest

**Structure**:

```python
# tests/unit/test_distance_estimator.py

import pytest
from src.vision.distance_estimator import DistanceEstimator

class TestDistanceEstimator:
    """Tests for DistanceEstimator class."""

    @pytest.fixture
    def estimator(self):
        """Create estimator instance for testing."""
        return DistanceEstimator(
            reference_height=200,
            reference_distance=1.0
        )

    def test_calculate_distance_normal(self, estimator):
        """Test distance calculation with valid input."""
        distance = estimator.calculate_distance(bbox_height=100)
        assert distance == pytest.approx(2.0, rel=0.01)

    def test_calculate_distance_zero_height(self, estimator):
        """Test handling of zero bbox height."""
        distance = estimator.calculate_distance(bbox_height=0)
        assert distance is None

    def test_calculate_distance_negative_height(self, estimator):
        """Test handling of negative bbox height."""
        distance = estimator.calculate_distance(bbox_height=-50)
        assert distance is None

    @pytest.mark.parametrize("height,expected", [
        (200, 1.0),
        (100, 2.0),
        (400, 0.5),
        (50, 4.0),
    ])
    def test_calculate_distance_various_heights(self, estimator, height, expected):
        """Test distance calculation for various bbox heights."""
        distance = estimator.calculate_distance(bbox_height=height)
        assert distance == pytest.approx(expected, rel=0.01)
```

### Integration Test Standards

**Purpose**: Test component interactions

**Example**:

```python
# tests/integration/test_tracking_pipeline.py

import pytest
import numpy as np
from src.vision.object_tracker import ObjectTracker
from src.vision.distance_estimator import DistanceEstimator
from src.control.motor_controller import MotorController
from src.navigation.object_follower import ObjectFollower

class TestTrackingPipeline:
    """Integration tests for object tracking pipeline."""

    @pytest.fixture
    def pipeline(self, mock_camera, mock_thunderborg):
        """Create full tracking pipeline."""
        tracker = ObjectTracker()
        estimator = DistanceEstimator()
        motors = MotorController(mock_thunderborg)
        follower = ObjectFollower(tracker, estimator, motors)
        return follower

    def test_full_tracking_cycle(self, pipeline):
        """Test complete tracking cycle from frame to motor commands."""
        # Create test frame with object
        frame = create_test_frame_with_object(position=(320, 240))

        # Initialize tracking
        pipeline.initialize(frame, bbox=(280, 200, 80, 80))

        # Process frame
        pipeline.update(frame)

        # Verify motor commands issued
        assert pipeline.motors.get_last_command() is not None
        assert -1.0 <= pipeline.motors.left_speed <= 1.0
        assert -1.0 <= pipeline.motors.right_speed <= 1.0
```

### Field Test Checklist

Before each field test session:

- [ ] Battery fully charged (>8V)
- [ ] ThunderBorg connected and responding
- [ ] Camera operational and focused
- [ ] Emergency stop button tested
- [ ] Connection watchdog tested
- [ ] Test area clear of obstacles
- [ ] Weather suitable (no rain, moderate temperature)
- [ ] WiFi connection stable
- [ ] Laptop/phone ready for control
- [ ] Backup plan if robot fails

During testing:

- [ ] Start with manual control, verify all directions
- [ ] Test emergency stop before autonomous modes
- [ ] Monitor battery voltage
- [ ] Document unexpected behaviors
- [ ] Take notes on performance
- [ ] Capture video for analysis (optional)

After testing:

- [ ] Log test results
- [ ] Note any issues or improvements needed
- [ ] Clean robot (dirt, debris)
- [ ] Disconnect battery if not using soon

---

## Documentation Standards

### Documentation Types

1. **Code Documentation** (Docstrings)
   - Every public function, class, method
   - Google style format
   - Include examples for complex functions

2. **User Documentation** (`docs/user_manual.md`)
   - How to use the web interface
   - How to configure settings
   - Troubleshooting common issues

3. **Developer Documentation** (`docs/architecture.md`)
   - System design decisions
   - Component interactions
   - Extending the system

4. **Installation Guide** (`docs/installation.md`)
   - Step-by-step Raspberry Pi setup
   - Dependency installation
   - First-time configuration

5. **API Documentation** (auto-generated with Sphinx)
   - Generated from docstrings
   - Hosted on GitHub Pages or Read the Docs

### README Requirements

**Must Include**:

- Project description (1-2 paragraphs)
- Features list
- Hardware requirements
- Quick start guide (5 minutes to running)
- Links to detailed documentation
- License information
- Contribution guidelines link
- Screenshots/GIFs of robot in action

**Template**:

```markdown
# MonsterBorg Self-Drive

[Brief description]

## Features
- Mobile web controls
- Autonomous object tracking
- ...

## Quick Start

1. Flash Raspberry Pi OS
2. Clone repository: `git clone ...`
3. Run install script: `./scripts/install_raspberry_pi.sh`
4. Start server: `python src/main.py`
5. Open browser: `http://monsterborg.local:8080`

## Documentation

- [User Manual](docs/user_manual.md)
- [Installation Guide](docs/installation.md)
- [Architecture](docs/architecture.md)

## License

MIT License - see LICENSE file

## Contributing

See [CONTRIBUTION_GUIDELINES.md](CONTRIBUTION_GUIDELINES.md)
```

### Inline Comments

**When to Comment**:

- Complex algorithms (explain approach)
- Non-obvious optimizations (explain why)
- Workarounds for bugs (link to issue)
- Magic numbers (explain significance)
- Business logic (explain reasoning)

**When NOT to Comment**:

- Obvious code (name already explains it)
- Restating what code does (use better names instead)

**Examples**:

```python
# GOOD: Explains WHY
# Use smaller resolution for processing to achieve 30 fps on Pi 3B
scaled_frame = cv2.resize(frame, (160, 120))

# GOOD: Explains non-obvious algorithm
# Dual PID: position error keeps us on track, change error handles curves
position_output = self.position_pid.update(offset)
change_output = self.change_pid.update(offset_change)

# GOOD: Explains workaround
# Workaround for OpenCV issue #12345: KCF tracker fails on first frame
# Initialize with dummy frame before real tracking starts
self.tracker.init(dummy_frame, initial_bbox)

# BAD: States the obvious
# Set speed to 0.5
speed = 0.5

# BAD: Restates code
# Loop through all items in the list
for item in items:
    process(item)
```

---

## Version Control Practices

### Branching Strategy

**Model**: GitHub Flow (simplified Git Flow)

**Branches**:

- `main`: Production-ready code (always stable)
- `feature/feature-name`: New features
- `fix/bug-name`: Bug fixes
- `docs/topic`: Documentation updates
- `refactor/component`: Code refactoring

**Rules**:

- Never commit directly to `main`
- Always work in feature branches
- Merge via Pull Request with review
- Delete branch after merge
- Keep branches short-lived (<1 week)

### Commit Practices

**Atomic Commits**: Each commit should be a single logical change

**Good Example**:

```bash
git commit -m "feat(tracking): add KCF tracker implementation"
git commit -m "test(tracking): add unit tests for KCF tracker"
git commit -m "docs(tracking): document KCF tracker usage"
```

**Bad Example** (too large, multiple changes):

```bash
git commit -m "add tracking, fix bugs, update docs"
```

### Commit Hygiene

Before committing:

```bash
# 1. Run formatter
black .

# 2. Run linter
flake8 .

# 3. Run type checker
mypy src/

# 4. Run tests
pytest

# 5. Check what you're committing
git diff --staged

# 6. Commit with descriptive message
git commit -m "type(scope): description"
```

### Pre-Commit Hooks

**Tool**: `pre-commit`

**Configuration** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.0.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
        args: [--profile=black]
```

**Install**:

```bash
pip install pre-commit
pre-commit install
```

Now quality checks run automatically before each commit.

---

## Release Management

### Versioning

**Scheme**: Semantic Versioning (SemVer)

**Format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible API)
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

**Examples**:

- `1.0.0`: Initial stable release
- `1.1.0`: Add object tracking feature
- `1.1.1`: Fix distance calculation bug
- `2.0.0`: Refactor with breaking config changes

### Release Process

1. **Update CHANGELOG.md**
   - Move items from Unreleased to new version section
   - Follow Keep a Changelog format

2. **Update Version**
   - In `src/__init__.py`: `__version__ = "1.1.0"`
   - In `setup.py` (if used)

3. **Create Git Tag**

   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

4. **Create GitHub Release**
   - Go to repository → Releases → Draft a new release
   - Select tag
   - Copy CHANGELOG entry for release notes
   - Attach any binaries (optional)

5. **Announce**
   - Update README with new version
   - Post in discussions/forum
   - Tweet (if project has social media)

### CHANGELOG Format

**File**: `CHANGELOG.md`

**Example**:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial work on machine learning object classification

### Changed
- Improved distance estimation accuracy

## [1.1.0] - 2025-11-20

### Added
- Object tracking and following mode
- Re-acquisition algorithm
- Inverted operation support
- Mobile-optimized web interface

### Fixed
- Motor direction bug when inverted
- WebSocket connection stability

## [1.0.0] - 2024-12-01

### Added
- Initial line-following functionality
- Web control interface
- ThunderBorg integration

[Unreleased]: https://github.com/user/repo/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/user/repo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/user/repo/releases/tag/v1.0.0
```

---

## Governance

### Project Leadership

**Maintainer**: dxcSithLord (repository owner)

**Responsibilities**:

- Final decision on major architectural changes
- Release approval
- Merge pull requests
- Community moderation

### Decision Making

**Process**:

1. **Propose**: Open issue describing proposal
2. **Discuss**: Community provides feedback
3. **Decide**: Maintainer makes final call (usually consensus)
4. **Document**: Decision recorded in issue/ADR

**For Major Changes**:

- Requires discussion and approval
- Examples: Architecture changes, breaking changes, new dependencies

**For Minor Changes**:

- Can be merged with single review approval
- Examples: Bug fixes, documentation, small features

### Architecture Decision Records (ADRs)

**Purpose**: Document significant architectural decisions

**Location**: `docs/adr/`

**Format**:

```markdown
# ADR 001: Use OpenCV for Object Tracking

## Status
Accepted

## Context
Need robust object tracking for following mode. Several options available:
- OpenCV built-in trackers (KCF, CSRT)
- TensorFlow Lite object detection
- Custom implementation

## Decision
Use OpenCV KCF tracker as primary method, with CSRT as fallback.

## Rationale
- OpenCV already dependency for camera
- KCF fast enough for Pi 3B (30+ fps)
- CSRT more accurate when speed less critical
- No additional dependencies needed
- Well-documented and battle-tested

## Consequences
- Positive: Fast implementation, good performance
- Negative: Limited to visual tracking (no semantic understanding)
- Mitigation: Can add TF Lite later for classification

## Alternatives Considered
- TensorFlow Lite: Too slow on Pi 3B (~5 fps)
- Custom correlation tracker: Unnecessary complexity
```

---

## Amendment Process

### How to Propose Amendments

This constitution is a living document. To propose changes:

1. **Open Issue**
   - Title: "Constitution Amendment: [topic]"
   - Description: Proposed change and rationale

2. **Discuss**
   - Community provides feedback
   - Iterate on proposal

3. **Vote** (if contentious)
   - Maintainer calls for vote
   - Simple majority of active contributors

4. **Merge**
   - Create PR updating this document
   - Update revision history below

### Revision History

|Version|Date|Author|Changes|
|------|------|--------|--------|
|1.0|2025-11-14|Claude|Initial constitution|

---

## Acknowledgments

This constitution draws inspiration from:

- Python Enhancement Proposals (PEPs)
- Linux Kernel Coding Style
- Google Style Guides
- Contributor Covenant
- Conventional Commits

---

## Contact

**Repository**: <https://github.com/dxcSithLord/monster-self-drive>
**Issues**: <https://github.com/dxcSithLord/monster-self-drive/issues>
**Discussions**: <https://github.com/dxcSithLord/monster-self-drive/discussions>

---

**By contributing to this project, you agree to abide by this constitution.**

---

## End of Project Constitution
