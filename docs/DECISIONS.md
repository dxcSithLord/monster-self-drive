# Architectural Decision Records (ADR)

**Purpose:** Track all major architectural decisions for the Monster Self-Drive project
**Format:** Based on [Michael Nygard's ADR format](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
**Status:** Decision tracking started 2025-12-06

---

## How to Use This Document

Each architectural decision should include:

1. **Context** - The issue motivating this decision
2. **Decision** - The change that we're proposing or have agreed to
3. **Status** - Proposed, Accepted, Deprecated, Superseded
4. **Consequences** - What becomes easier or more difficult
5. **Alternatives Considered** - Other options and why they were rejected

---

## ADR Index

| ID | Title | Status | Date | Priority |
|----|-------|--------|------|----------|
| ADR-001 | WebSocket Library Selection | 🟢 Accepted | 2025-12-06 | P0 |
| ADR-002 | Configuration Format | 🟢 Accepted | 2025-12-06 | P1 |
| ADR-003 | Directory Structure | 🟢 Accepted | 2025-12-06 | P1 |
| ADR-004 | Multi-User Control Model | 🟢 Accepted | 2025-12-06 | P0 |
| ADR-005 | Tracking Algorithm Strategy | 🟢 Accepted | 2025-12-06 | P1 |
| ADR-006 | IMU Hardware Status | 🟢 Accepted | 2025-12-06 | P3 |
| ADR-007 | Frame Rate Requirements | 🟢 Accepted | 2025-12-07 | P1 |
| ADR-008 | Threading Model | 🟢 Accepted | 2025-12-07 | P1 |
| ADR-009 | Safety System Architecture | 🟢 Accepted | 2025-12-07 | P0 |
| ADR-010 | GPIO Pin Assignments | 🟢 Accepted | 2025-12-07 | P0 |

**Status Legend:**

- 🟡 Proposed - Under consideration
- 🟢 Accepted - Decision made and documented
- 🔴 Deprecated - No longer valid
- 🔵 Superseded - Replaced by another ADR

---

## ADR-001: WebSocket Library Selection

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P0 - Must resolve before Phase 1

### Context

The system requires bidirectional real-time communication between web clients and the Raspberry Pi for:

- Motor control commands (low latency critical)
- Video streaming
- Sensor data updates
- Status information

Two libraries mentioned in documentation:

1. **websockets** (asyncio-based)
2. **Flask-SocketIO** (Socket.IO protocol)

This is a BLOCKING decision because it fundamentally affects:

- Threading model (async vs. sync/gevent)
- Architecture patterns
- Client-side implementation
- Performance characteristics

### Decision

**ACCEPTED: Flask-SocketIO**

The project will use **Flask-SocketIO** for real-time WebSocket communication.

**Rationale:**

1. **Framework Compatibility:** Integrates seamlessly with the existing Flask framework currently used in `monsterWeb.py`
2. **Performance Adequate:** Expected latency (20-30ms) is acceptable given that only one user will have active control at any time
3. **Multi-User Support:** Supports the planned control model where:
   - One user has active control
   - Second user can request to take over control
   - Second user can access when first user disconnects
4. **Lower Migration Risk:** Minimal changes required to existing synchronous codebase
5. **Reliability:** Built-in automatic reconnection is crucial for remote robot control

**Implementation Details:**

- Library: `Flask-SocketIO >= 3.0`
- Update `requirements.txt` to include Flask-SocketIO
- Async mode: Start with threading mode, can upgrade to asyncio if needed
- Client-side: socket.io-client for JavaScript

### Options Analysis

#### Option 1: `websockets` library (asyncio)

**Pros:**

- Native Python asyncio support (Python 3.7+)
- Lower-level control over WebSocket protocol
- Lightweight and fast
- No framework lock-in
- Better for high-performance scenarios
- Simpler protocol (just WebSocket, no Socket.IO overhead)

**Cons:**

- Requires full asyncio architecture
- More complex integration with existing synchronous code
- Need to handle reconnection logic manually
- Client-side must use native WebSocket (no Socket.IO client)
- Steeper learning curve

**Technical Implications:**

```python
# Would require async architecture:
async def motor_control_handler(websocket, path):
    async for message in websocket:
        await process_motor_command(message)

# All I/O becomes async
async def read_sensors():
    while True:
        data = await sensor.read()
        await websocket.send(data)
```

#### Option 2: Flask-SocketIO

**Pros:**

- Integrates seamlessly with existing Flask (if using Flask)
- Socket.IO protocol provides:
  - Automatic reconnection
  - Fallback transports (polling if WebSocket fails)
  - Room/namespace support
- Easier to mix sync and async code
- Rich client library ecosystem (socket.io-client)
- Better browser compatibility

**Cons:**

- Heavier than plain WebSocket
- Requires eventlet or gevent (monkey patching concerns)
- Framework dependency (Flask)
- Slightly higher latency due to protocol overhead
- More complex debugging

**Technical Implications:**

```python
# Can use synchronous patterns:
@socketio.on('motor_command')
def handle_motor_command(data):
    process_motor_command(data)

# Or async with async_mode='asyncio'
```

#### Option 3: Alternative - `socket.io` (standalone, no Flask)

**Pros:**

- Socket.IO benefits without Flask dependency
- Can use asyncio mode
- More flexible than Flask-SocketIO

**Cons:**

- Less documentation than Flask-SocketIO
- Still requires event loop management

### Evaluation Criteria

| Criterion | websockets | Flask-SocketIO | Weight |
|-----------|------------|----------------|--------|
| **Latency** | ⭐⭐⭐⭐⭐ (10-20ms) | ⭐⭐⭐⭐ (20-30ms) | High |
| **Reliability** | ⭐⭐⭐ (manual retry) | ⭐⭐⭐⭐⭐ (auto reconnect) | High |
| **Ease of Integration** | ⭐⭐ (requires refactor) | ⭐⭐⭐⭐ (fits existing) | Medium |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Medium |
| **Browser Support** | ⭐⭐⭐⭐ (modern only) | ⭐⭐⭐⭐⭐ (fallbacks) | Low |
| **Learning Curve** | ⭐⭐ (asyncio complex) | ⭐⭐⭐⭐ (simpler) | Medium |

### Current Codebase Analysis

**Existing Code Review:**

- `monsterWeb.py` uses Flask framework
- Current architecture is synchronous
- No async patterns currently used
- Threading used for video streaming

**Migration Effort:**

- **To websockets:** HIGH - Full async refactor needed
- **To Flask-SocketIO:** LOW - Drop-in replacement for Flask routes

### Recommendation

**✅ DECISION ACCEPTED**

**Selected:** Flask-SocketIO (Option 2)

This recommendation was accepted based on:

1. Current codebase uses Flask (easier integration)
2. Synchronous code can remain mostly unchanged
3. Automatic reconnection crucial for remote robot control
4. Latency difference (10-20ms) acceptable for single-user control model
5. Lower implementation risk

**Future Consideration:** If performance profiling shows unacceptable latency after implementation, consider migrating to `websockets` in Phase 2+.

### Consequences if Accepted

**Positive:**

- Quick integration with existing Flask code
- Reliable connection handling
- Rich client-side library
- Easier testing and debugging

**Negative:**

- Slight latency overhead
- Dependency on Flask framework
- Need to choose async_mode (eventlet/gevent/asyncio)

**Migration Path:**

- Start with Flask-SocketIO in threading mode
- Profile performance
- If needed, switch to async_mode='asyncio'
- If still needed, consider full websockets migration

### Action Items

- [x] Decision maker assigned
- [x] Decision made: Flask-SocketIO selected
- [ ] Update requirements.txt to include Flask-SocketIO
- [ ] Update REQUIREMENTS.md with chosen library
- [ ] Update IMPLEMENTATION_PLAN.md with architecture details
- [ ] Implement Flask-SocketIO in monsterWeb.py (Phase 1)
- [ ] Performance testing after implementation

---

## ADR-002: Configuration Format

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P1 - Resolve before Phase 1

### Context

Configuration is currently stored in `Settings.py` (Python module), but documentation mentions "JSON or INI". Inconsistency causes confusion and affects:

- Configuration management
- User editability
- Validation
- Deployment automation

### Decision

**ACCEPTED: JSON Configuration with Python Wrapper**

The project will use **JSON** as the primary configuration storage format with a Python wrapper for validation and access.

**Implementation Approach:**

1. **Configuration Storage:** JSON file containing all settings key-value pairs
2. **Settings.py Role:** Import and validate JSON configuration at startup
3. **Web Interface:** Configuration view page to display/confirm current settings
4. **Migration:** Convert existing Settings.py key-value pairs to JSON format

**Rationale:**

1. **Industry Standard:** JSON is widely understood and supported
2. **Schema Validation:** Can implement JSON Schema validation for type safety
3. **Web Integration:** Easy to serialize/deserialize for web configuration interface
4. **Editability:** Users can edit JSON file directly or via web interface
5. **Validation Layer:** Settings.py provides Python validation and default values
6. **Language Agnostic:** Future tools can read configuration without Python

### Options Analysis

#### Option 1: Keep `Settings.py` (Python module)

**Current Implementation:**

```python
# Settings.py
imageWidth = 320
imageHeight = 240
frameRate = 10
# ...
```

**Pros:**

- Already implemented
- No migration needed
- Python syntax validation
- Can include computed values
- Native type handling

**Cons:**

- Requires Python knowledge to edit
- Harder for non-developers
- Must reload code to change config
- No runtime validation
- Security risk if user-provided

**Use Case:** Developer-focused projects

#### Option 2: JSON Configuration

**Example:**

```json
{
  "camera": {
    "width": 320,
    "height": 240,
    "frameRate": 10
  },
  "motor": {
    "maxPower": 0.8
  }
}
```

**Pros:**

- Industry standard
- Easy to parse and generate
- Schema validation available (JSON Schema)
- Widely understood
- Hierarchical structure
- Language-agnostic

**Cons:**

- No comments support (without extensions)
- Strict syntax (trailing commas break parsing)
- Less human-friendly than YAML/INI

**Use Case:** API-driven, automated deployments

#### Option 3: INI Configuration

**Example:**

```ini
[camera]
width = 320
height = 240
frameRate = 10

[motor]
maxPower = 0.8
```

**Pros:**

- Very human-readable
- Simple syntax
- Comments supported
- Forgiving parsing
- Familiar to many users

**Cons:**

- Limited nesting (flat structure)
- Type inference needed (all strings)
- Less tooling than JSON
- No standard schema validation

**Use Case:** User-edited configuration files

#### Option 4: YAML Configuration

**Example:**

```yaml
camera:
  width: 320
  height: 240
  frameRate: 10

motor:
  maxPower: 0.8
```

**Pros:**

- Very readable
- Comments supported
- Good nesting support
- Type inference
- Popular in DevOps

**Cons:**

- Whitespace-sensitive (error-prone)
- Security concerns (arbitrary code execution in some parsers)
- Requires external library

#### Option 5: TOML Configuration

**Example:**

```toml
[camera]
width = 320
height = 240
frameRate = 10

[motor]
maxPower = 0.8
```

**Pros:**

- Designed for config files
- Comments supported
- Type-aware
- Growing adoption (pyproject.toml)
- Better than INI for nested data

**Cons:**

- Less familiar than JSON/INI
- Requires external library

### Evaluation Criteria

| Criterion | Settings.py | JSON | INI | YAML | TOML |
|-----------|-------------|------|-----|------|------|
| **User-Editable** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Validation** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Hierarchy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Comments** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **No Migration** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ | ⭐ |
| **Std Library** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ |

### Recommendation

**✅ DECISION ACCEPTED**

**Selected:** JSON Configuration with Python Wrapper (Hybrid of Options 1 & 2)

**Final Implementation:**

```python
# Settings.py becomes a loader/validator:
import json
import jsonschema

class Settings:
    def __init__(self):
        self.load_config()

    def load_config(self):
        with open('config.json', 'r') as f:
            config = json.load(f)
        self.validate(config)
        # Set attributes from config

    def validate(self, config):
        # JSON Schema validation
        # Type checking
        # Range validation
```

**Web Interface Requirement:**

- Configuration view page in web interface
- Display all current settings (read-only for MVP)
- Future: Allow editing through web UI

### Migration Plan

**If changing from Settings.py:**

1. **Phase 1:** Create config file reader

   ```python
   def load_config():
       if os.path.exists('config.json'):
           return load_json('config.json')
       # Fallback to Settings.py
       return import_settings_py()
   ```

2. **Phase 2:** Generate default config from Settings.py

   ```bash
   python -m monster.tools.export_config > config.json
   ```

3. **Phase 3:** Add validation schema

4. **Phase 4:** Deprecate Settings.py (keep as defaults)

### Consequences

**Positive:**

- Clear configuration location (config.json)
- User can edit JSON directly or via web interface
- JSON Schema validation prevents errors
- Settings.py provides Python-level validation layer
- Easy to serialize for web interface display
- Language-agnostic configuration format

**Negative:**

- Migration effort required (convert Settings.py to JSON)
- Need to implement JSON Schema
- Potential for JSON syntax errors (mitigated by web interface)
- No comments in JSON (can use JSON5 or document separately)

### Action Items

- [x] Choose format - JSON with Python wrapper selected
- [ ] Convert current Settings.py key-value pairs to config.json
- [ ] Refactor Settings.py to load and validate JSON
- [ ] Create JSON Schema for validation
- [ ] Implement web UI configuration view page
- [ ] Update documentation with JSON structure
- [ ] Create example config.json file

---

## ADR-003: Directory Structure

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P1 - Resolve before Phase 1

### Context

Current codebase has flat structure in root directory. CONSTITUTION proposes `src/` based structure. Need to decide:

- Migrate to src/ structure OR keep flat
- When to migrate (before or during development)
- Import path changes
- **Requirement:** Separation of source and release components

### Current Structure

```
monster-self-drive/
├── ImageProcessor.py
├── MonsterAuto.py
├── Settings.py
├── ThunderBorg.py
└── monsterWeb.py
```

### Decision

**ACCEPTED: Structured Approach with Source/Release Separation**

The project will migrate to a structured directory layout that separates source code from release/deployment components.

**Rationale:**

1. **Separation of Concerns:** Source code separated from configuration, documentation, and release artifacts
2. **Scalability:** Better organization as project grows (currently 5 files, will expand significantly)
3. **Professional Structure:** Follows Python best practices for larger projects
4. **Build Process:** Clear separation enables proper build/release workflows
5. **Testability:** Easier to organize tests alongside source code

**Proposed Structure:**

```
monster-self-drive/
├── src/                    # Source code
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py     # Config loader/validator
│   │   └── monster_auto.py
│   ├── web/
│   │   ├── __init__.py
│   │   └── web_server.py   # Flask-SocketIO server
│   ├── vision/
│   │   ├── __init__.py
│   │   ├── image_processor.py
│   │   └── tracking.py     # Color-based tracking
│   ├── hardware/
│   │   ├── __init__.py
│   │   ├── thunderborg.py
│   │   └── motors.py
│   └── safety/
│       ├── __init__.py
│       ├── control_manager.py  # Single user control
│       └── emergency_stop.py
├── config/                 # Configuration files
│   ├── config.json         # Runtime configuration
│   └── config.schema.json  # JSON Schema
├── docs/                   # Documentation (existing)
├── tests/                  # Test files
│   ├── unit/
│   └── integration/
├── release/                # Release artifacts (git-ignored)
│   ├── dist/
│   └── build/
├── static/                 # Web UI assets
│   ├── css/
│   ├── js/
│   └── img/
├── templates/              # Flask templates
├── requirements.txt
├── setup.py               # Python package setup
└── README.md
```

### Options

#### Option 1: Keep Flat Structure

**Pros:**

- No migration needed
- Simpler imports: `import MonsterAuto`
- No namespace packages
- Easier for small projects

**Cons:**

- Less organized as project grows
- All files in one directory
- Harder to separate concerns
- Not following Python best practices for larger projects

#### Option 2: Migrate to src/ Structure

**Pros:**

- Better organization
- Clear separation of concerns
- Scalable for growth
- Follows modern Python packaging standards
- Easier testing (import from src)

**Cons:**

- Requires migration effort
- Import paths change: `from src.core import monster_auto`
- Potential compatibility issues during transition

#### Option 3: Hybrid (gradual migration)

**Pros:**

- Can migrate incrementally
- Lower risk

**Cons:**

- Confusing during transition
- Import path inconsistency

### Recommendation

**✅ DECISION ACCEPTED**

**Selected:** Structured approach with source/release separation (Enhanced Option 2)

**Migration Timing:** BEFORE Phase 1 implementation begins

**Rationale:**

1. Project will grow significantly (MVP alone requires 10+ new modules)
2. Better to migrate early (less code to change now than later)
3. Clearer organization helps contributors and maintenance
4. Testing benefits from src/ separation
5. **Release separation** requirement addressed with dedicated release/ directory

### Migration Plan

```bash
# Step 1: Create new directory structure
mkdir -p src/{core,web,vision,hardware,safety}
mkdir -p config
mkdir -p tests/{unit,integration}
mkdir -p release/{dist,build}
mkdir -p static/{css,js,img}
mkdir -p templates

# Step 2: Move existing files
mv MonsterAuto.py src/core/monster_auto.py
mv monsterWeb.py src/web/web_server.py
mv ImageProcessor.py src/vision/image_processor.py
mv ThunderBorg.py src/hardware/thunderborg.py
mv Settings.py src/core/settings.py  # Will refactor to JSON loader

# Step 3: Add __init__.py files
touch src/__init__.py
touch src/{core,web,vision,hardware,safety}/__init__.py

# Step 4: Update imports in all files
# Example: from src.core.settings import Settings

# Step 5: Add release/ to .gitignore
echo "release/" >> .gitignore

# Step 6: Update README and documentation with new structure
```

### Consequences

**Positive:**

- Better code organization
- Easier to navigate
- Professional structure
- Easier testing

**Negative:**

- One-time migration effort (~2-4 hours)
- Import statements need updates
- Documentation needs updates

### Action Items

- [x] Approve migration decision - ACCEPTED: Structured source/release separation
- [ ] Execute migration plan (create directories, move files)
- [ ] Update all imports to use src.* paths
- [ ] Create setup.py for package management
- [ ] Add release/ to .gitignore
- [ ] Update README with new structure
- [ ] Update IMPLEMENTATION_PLAN.md with new paths
- [ ] Test all modules after migration

---

## ADR-004: Multi-User Control Model

**Status:** 🟢 ACCEPTED (SAFETY CRITICAL)
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P0 - Safety blocker

### Context

REQUIREMENTS specify "3 simultaneous connections" but don't define control arbitration. Critical safety issue:

- What happens when multiple users send conflicting commands?
- Who has control of the robot?
- How to prevent dangerous situations?

### Decision

**ACCEPTED: Single Active User Model (Option 1)**

The project will implement a **single active user** control model with the following characteristics:

**Control Model:**

- Only ONE user has active control at any time
- Other connected users are in "observer mode" (video feed only, controls disabled)
- Control handoff mechanisms:
  - Second user can **request to take over** control
  - Second user automatically gains access when first user **disconnects**
  - Optional: Active user can voluntarily **release control**

**Rationale:**

1. **Safety First:** Eliminates possibility of conflicting commands that could cause dangerous robot behavior
2. **Clarity:** Always clear who is responsible for robot control
3. **Simplicity:** Straightforward to implement and understand
4. **Performance:** Aligns with single-user performance expectations (no latency concerns)
5. **Emergency Override:** ANY connected user can trigger emergency stop, regardless of control status

### Safety Scenarios

**Scenario 1: Conflicting Drive Commands**

- User A: Forward full speed
- User B: Backward full speed
- Simultaneous arrival at robot
- **Result:** ???

**Scenario 2: Mode Switching**

- User A: Autonomous mode active
- User B: Switches to manual mode
- **Result:** Does autonomous stop? Emergency?

**Scenario 3: Emergency Stop**

- User A: Driving robot
- User B: Presses emergency stop
- **Result:** Should User B be able to stop User A?

### Options

#### Option 1: Single Active User (Recommended)

**Control Model:**

- Only ONE user has control at a time
- Other users are "observers" (view-only)
- Explicit handoff required

**Implementation:**

```python
active_user = None

def handle_command(user_id, command):
    if user_id != active_user:
        return {"error": "Not active user"}
    execute_command(command)
```

**Pros:**

- Clear responsibility
- No conflicting commands
- Safer operation
- Simple to implement

**Cons:**

- Only one driver at a time
- Need handoff mechanism

**Handoff Options:**

- A: Active user releases control (button)
- B: Request/grant system
- C: Timeout after inactivity

#### Option 2: Last-Command-Wins

**Control Model:**

- Any connected user can send commands
- Latest command takes precedence
- No explicit control assignment

**Implementation:**

```python
def handle_command(user_id, command):
    # No check, just execute
    execute_command(command)
    last_command_user = user_id
```

**Pros:**

- Simple implementation
- No handoff needed
- Any user can intervene

**Cons:**

- ⚠️ DANGEROUS: Conflicting commands
- Command oscillation possible
- Unclear who's driving
- Accidental interference

#### Option 3: Priority-Based

**Control Model:**

- Users have priority levels (admin > user > guest)
- Higher priority can override lower
- Equal priority = last-command-wins

**Implementation:**

```python
user_priorities = {"admin": 3, "user": 2, "guest": 1}

def handle_command(user_id, command):
    if user_priority[user_id] < current_controller_priority:
        return {"error": "Insufficient priority"}
    execute_command(command)
```

**Pros:**

- Admin can always take control
- Guests can't interfere
- Flexible hierarchy

**Cons:**

- More complex
- Need user management
- Priority conflicts still possible

#### Option 4: Collaborative (Multi-Input Averaging)

**Control Model:**

- Average all user inputs
- Weighted by connection quality or role

**Pros:**

- Novel approach
- True multi-user

**Cons:**

- ⚠️ VERY DANGEROUS for robot control
- Unpredictable behavior
- Not recommended

### Recommendation

**✅ DECISION ACCEPTED**

**Selected:** Option 1 - Single Active User

**Implementation Requirements:**

1. **Emergency Stop:** ANY user can trigger (broadcasts to all) - CRITICAL SAFETY FEATURE
2. **Observer Mode:** Non-active users see video but UI disabled
3. **Control Request:** Request/grant system for control takeover
4. **Automatic Handoff:** Control transfers when active user disconnects
5. **Timeout:** Optional auto-release control after inactivity period (TBD: 5 min?)
6. **UI Indicator:** Large UI banner showing who has control

### UI Design

**Active User:**

```
┌─────────────────────────────────────┐
│ ● YOU HAVE CONTROL                   │
│ Release Control [Button]             │
└─────────────────────────────────────┘
[Enabled joystick/controls]
```

**Observer:**

```
┌─────────────────────────────────────┐
│ 👁️ OBSERVER MODE                     │
│ Alice has control                    │
│ Request Control [Button]             │
└─────────────────────────────────────┘
[Disabled/grayed controls]
```

### Implementation Details

```python
class ControlManager:
    def __init__(self):
        self.active_user = None
        self.control_queue = []
        self.last_activity = {}

    def request_control(self, user_id):
        if self.active_user is None:
            self.grant_control(user_id)
        else:
            self.control_queue.append(user_id)
            self.notify_active_user(f"{user_id} requesting control")

    def release_control(self, user_id):
        if user_id == self.active_user:
            self.active_user = None
            if self.control_queue:
                next_user = self.control_queue.pop(0)
                self.grant_control(next_user)

    def emergency_stop(self, user_id):
        # ANY user can trigger - broadcasts to all
        stop_robot()
        self.active_user = None
        broadcast_message("EMERGENCY STOP by " + user_id)
```

### Consequences

**Positive:**

- Safe operation
- Clear control model
- Prevents accidents
- Good user experience

**Negative:**

- Only one driver at a time
- Need request/release UI
- Slightly more complex

### Action Items

- [x] Approve control model - ACCEPTED: Single Active User
- [x] Define control handoff mechanisms (request takeover, auto-transfer on disconnect)
- [ ] Design UI mockups for active/observer modes
- [ ] Implement ControlManager class in monsterWeb.py
- [ ] Add control indicators to web UI (banner showing control status)
- [ ] Implement emergency stop for ANY user
- [ ] Test control handoff scenarios
- [ ] Document control model in user guide
- [ ] Update REQUIREMENTS.md with control model specification

---

## ADR-005: Tracking Algorithm Strategy

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P1 - Needed before Phase 2

### Context

Multiple tracking algorithms mentioned (KCF, CSRT, MOSSE, Template, Color) but no clear strategy for which to implement when.

**Constraints:**

- Must function within Raspberry Pi 3B limitations
- Limited CPU resources (4-core ARM Cortex-A53 @ 1.2GHz)
- Limited memory (1GB RAM)
- Real-time performance required (target 30 fps)

### Decision

**ACCEPTED: Color-Based Tracking for MVP**

The project will implement **color-based tracking** as the primary tracking algorithm for the MVP (Phase 2).

**Rationale:**

1. **Performance:** Lightest computational load, suitable for Raspberry Pi 3B
2. **Simplicity:** Easiest to implement and debug
3. **Real-time Capable:** Can achieve 30 fps on Pi 3B hardware
4. **Sufficient for MVP:** Adequate for controlled environment testing
5. **Foundation:** Provides baseline for future algorithm comparison

**MVP Implementation:**

- HSV color space tracking (more robust than RGB)
- Configurable color range via web interface
- Bounding box detection
- Centroid calculation for target position

**Future Enhancements (Post-MVP):**

- Phase 3: Add MOSSE tracker as fallback (fast, lightweight)
- Phase 4: Consider KCF for improved robustness
- Phase 5: Hybrid approach with algorithm selection

**Performance Targets:**

- Target FPS: 30 fps minimum
- Acceptable FPS: 15 fps (degraded mode)
- Processing time budget: <33ms per frame

### Algorithm Comparison

| Algorithm | CPU Load | Accuracy | FPS on Pi 3B | Complexity |
|-----------|----------|----------|--------------|------------|
| **Color-based** | ⭐ (lowest) | ⭐⭐ | 30+ fps | Low |
| MOSSE | ⭐⭐ | ⭐⭐⭐ | 25-30 fps | Medium |
| KCF | ⭐⭐⭐ | ⭐⭐⭐⭐ | 15-20 fps | Medium |
| CSRT | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 8-12 fps | High |

**Decision:** Color-based selected for MVP due to lowest CPU load and highest FPS

### Action Items

- [x] Choose algorithm for MVP - Color-based tracking selected
- [ ] Implement HSV color-based tracking in src/vision/tracking.py
- [ ] Add color range configuration to web UI
- [ ] Performance test on Raspberry Pi 3B hardware
- [ ] Document tracking algorithm in IMPLEMENTATION_PLAN.md
- [ ] Create fallback plan if performance inadequate

---

## ADR-006: IMU Hardware Status and Inversion Detection

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-06
**Decision Date:** 2025-12-06
**Deciders:** Project Lead
**Priority:** P3 - Future enhancement

### Context

Documentation shows conflicting information about IMU (Inert

ial Measurement Unit) requirements:

- REQUIREMENTS lists as "Recommended Additional Hardware" (optional)
- CONSTITUTION treats as "Integrated module" (required)
- Need to determine inversion detection method for robot

**Constraint:** Minimize additional hardware requirements for MVP

### Decision

**ACCEPTED: IMU Optional - Image-Based Inversion Detection for MVP**

**MVP Approach (No Additional Hardware):**

- IMU is **OPTIONAL** for MVP
- Inversion detection via **image analysis**
- No additional sensors required initially

**Inversion Detection Algorithm:**

1. **Image Analysis Method:**
   - Analyze camera image for orientation indicators
   - Look for expected features (sky, floor, known objects)
   - Color distribution analysis (floor vs ceiling colors)
   - Feature detection (if features inverted/upside-down)

2. **Indeterminate Result Handling:**
   - If image analysis inconclusive → Rotate 360° and re-assess
   - After rotation: Re-analyze image for orientation
   - Maximum attempts: 3 rotations/re-assessments

3. **SOS Emergency Mode:**
   - If still indeterminate after 3 attempts → **STOP VEHICLE**
   - Flash onboard LED in SOS Morse code pattern
   - SOS Pattern: `... --- ...` (3 short, 3 long, 3 short)
   - Timing:
     - Short flash: 0.2 seconds ON
     - Long flash: 0.6 seconds ON
     - Gap between flashes: 0.2 seconds OFF
     - Gap between pattern repetitions: 2.0 seconds
   - Repeat SOS pattern until user intervention

**Future Enhancement (Post-MVP):**

- Phase 5+: Add IMU for reliable orientation detection
- IMU provides definitive tilt/orientation data
- Image-based method remains as fallback

### Implementation Specification

**Image-Based Inversion Detection:**

```python
def detect_inversion(image):
    """
    Analyze image to determine if vehicle is inverted.
    Returns: 'normal', 'inverted', or 'indeterminate'
    """
    # Implementation strategies:
    # 1. Color histogram analysis (floor vs ceiling)
    # 2. Edge detection orientation
    # 3. Feature matching against known upright images
    # 4. Horizon detection
    pass

def handle_indeterminate_orientation():
    """
    Handle indeterminate orientation detection.
    """
    for attempt in range(3):
        rotate_360_degrees()
        result = detect_inversion(capture_image())
        if result != 'indeterminate':
            return result

    # After 3 failed attempts
    emergency_stop()
    flash_sos_pattern()
```

**SOS LED Flash Pattern:**

```python
def flash_sos_pattern():
    """
    Flash LED in SOS Morse code pattern.
    ... --- ... (repeat)
    """
    SHORT_FLASH = 0.2  # seconds
    LONG_FLASH = 0.6   # seconds
    FLASH_GAP = 0.2    # seconds
    PATTERN_GAP = 2.0  # seconds

    while True:  # Until user intervention
        # Three short flashes (S)
        for _ in range(3):
            led_on()
            time.sleep(SHORT_FLASH)
            led_off()
            time.sleep(FLASH_GAP)

        # Three long flashes (O)
        for _ in range(3):
            led_on()
            time.sleep(LONG_FLASH)
            led_off()
            time.sleep(FLASH_GAP)

        # Three short flashes (S)
        for _ in range(3):
            led_on()
            time.sleep(SHORT_FLASH)
            led_off()
            time.sleep(FLASH_GAP)

        time.sleep(PATTERN_GAP)  # Wait before repeating
```

### Odometry Measurements

**Available Measurements:**

- Motor rotation counts (encoder ticks)
- Movement detected in camera (visual odometry)
- Time duration of motor operation

**No IMU means:**

- No accelerometer data
- No gyroscope data
- No magnetometer data
- Rely on motor feedback and visual analysis

### Rationale

1. **Cost Effective:** No additional hardware purchase required for MVP
2. **Sufficient for Testing:** Image-based detection adequate for controlled testing
3. **Safety Mechanism:** SOS pattern provides clear emergency indicator
4. **Future Upgrade Path:** Can add IMU later for production reliability
5. **Creative Solution:** 360° rotation provides additional data points

### Consequences

**Positive:**

- Lower hardware cost for MVP
- Simplified initial setup
- Forces robust image analysis implementation
- SOS pattern is universally recognizable
- Can add IMU as enhancement later

**Negative:**

- Image-based detection less reliable than IMU
- 360° rotation takes time and may be disruptive
- SOS mode requires user intervention to reset
- Limited orientation data for odometry

### Action Items

- [x] Decide IMU status - OPTIONAL for MVP
- [ ] Implement image-based inversion detection algorithm
- [ ] Implement 360° rotation procedure
- [ ] Implement SOS LED flash pattern
- [ ] Test inversion detection in various lighting conditions
- [ ] Document SOS recovery procedure in user guide
- [ ] Consider IMU addition for Phase 5+

---

## ADR-007: Frame Rate Requirements

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-07
**Decision Date:** 2025-12-07
**Deciders:** Project Lead
**Priority:** P1 - High Priority

### Context

Frame rate requirements were inconsistent across documentation:
- REQUIREMENTS.md stated "30 fps minimum"
- REQUIREMENTS.md also stated "60 fps preferred"
- IMPLEMENTATION_PLAN.md mentioned frame skipping (~15 fps effective)

This inconsistency affected:
- Hardware selection expectations
- Processing budget allocation
- Performance testing criteria
- Speed limiting logic

### Decision

**ACCEPTED: Adaptive Frame Rate with Speed Limiting**

The system will implement adaptive frame rate requirements tied to robot speed:

**Frame Rate Tiers:**
- **Minimum:** 15 fps → Maximum robot speed limited to 50%
- **Target:** 30 fps → 100% maximum speed available
- **Above Target:** >30 fps → No additional speed benefit

**Policy:** Quality over frame rate - skip frames if needed to maintain processing quality

### Rationale

1. **Hardware Reality:** Current Raspberry Pi + Camera V2 achieves 30fps with OpenCV color following
2. **Safety First:** Lower frame rates = lower max speed ensures safety
3. **Processing Priority:** Better to process fewer frames well than many frames poorly
4. **Graceful Degradation:** System remains functional at lower frame rates
5. **No Over-Engineering:** >30 fps provides no benefit given processing constraints

### Implementation Details

**Speed Limiting Logic:**
```python
if current_fps >= 30:
    max_speed = 1.0  # 100% power available
elif current_fps >= 15:
    max_speed = 0.5  # 50% power limit
else:
    max_speed = 0.0  # Stop - too slow for safe operation
```

**Frame Skip Strategy:**
- Skip frames when processing falls behind
- Maintain processing quality over quantity
- Display warning when <15 fps for >5 seconds

### Consequences

**Positive:**
- Clear performance expectations
- Automatic safety limiting
- Graceful degradation under load
- Realistic requirements for hardware

**Negative:**
- More complex speed controller logic
- Need FPS monitoring thread
- Warning UI needed for low frame rates

### Alternatives Considered

**Option A: Fixed 30 fps minimum (rejected)**
- Too strict for variable processing loads
- Would fail safety tests under load
- Not achievable with complex tracking algorithms

**Option B: No frame rate requirements (rejected)**
- Unsafe - could operate with very low fps
- No performance baseline
- Difficult to test

---

## ADR-008: Threading Model Architecture

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-07
**Decision Date:** 2025-12-07
**Deciders:** Project Lead
**Priority:** P1 - High Priority

### Context

The system requires multiple concurrent operations:
- Motor control (low latency critical)
- Safety monitoring (critical)
- Video streaming and processing
- Web server request handling

Thread priorities and coordination were undefined, risking:
- Deadlocks
- Priority inversion
- Safety delays
- Unpredictable performance

### Decision

**ACCEPTED: Priority-Based Threading with Safety-First Architecture**

**Thread Priority Hierarchy:**

1. **Tier 1 (Highest - Equal Priority):**
   - Motor Control Thread
   - Safety Monitor Thread

2. **Tier 2 (Medium Priority):**
   - Video Streaming Thread
   - Image Processing Thread

3. **Tier 3 (Lowest Priority):**
   - Web Server Thread

**Critical Linkage:** Web server stop button directly signals Safety Monitor Thread

### Thread Specifications

#### Motor Control Thread
- **Priority:** Highest (equal with Safety)
- **Responsibilities:**
  - Execute motor commands from control queue
  - Maintain ThunderBorg command rate (>4 Hz for failsafe)
  - Apply speed limiting based on FPS
- **Communication:** Receives from control command queue
- **Timeout:** 100ms max for queue reads

#### Safety Monitor Thread
- **Priority:** Highest (equal with Motor Control)
- **Responsibilities:**
  - Monitor battery voltage
  - Check motor drive faults
  - Watch communication timeout (via Watchdog)
  - Process emergency stop signals
- **Communication:** Shared event flags, can signal Motor Control
- **Polling Rate:** 10 Hz (100ms intervals)
- **Emergency Stop:** Immediate MotorsOff() call

#### Video Streaming Thread
- **Priority:** Medium
- **Responsibilities:**
  - Capture frames from camera
  - Provide frames to Image Processing
  - Maintain frame buffer
- **Target Rate:** 30 fps (adaptive)
- **Buffer:** 2-frame circular buffer

#### Image Processing Thread
- **Priority:** Medium
- **Responsibilities:**
  - Process frames for line/object tracking
  - Calculate steering commands
  - Update FPS metrics
- **Adaptive:** Can skip frames under load
- **Output:** Sends to control command queue

#### Web Server Thread
- **Priority:** Lowest
- **Responsibilities:**
  - Handle HTTP requests
  - Serve camera frames
  - Process manual control inputs
  - Signal watchdog on activity
- **Non-Blocking:** Uses existing monsterWeb.py architecture

### Inter-Thread Communication

**Control Command Queue:**
- Type: `queue.Queue(maxsize=10)`
- Producers: Image Processing, Web Server
- Consumer: Motor Control
- Policy: Newest command on full queue (LIFO behavior)

**Safety Event Flags:**
- Type: `threading.Event()`
- Emergency Stop: Any thread can set
- Battery Low: Safety Monitor sets
- Comm Timeout: Watchdog sets

**Frame Buffer:**
- Type: Circular buffer (2 frames)
- Lock: `threading.Lock()`
- Producer: Video Streaming
- Consumer: Image Processing, Web Server

### Deadlock Prevention

1. **Lock Ordering:** Always acquire in order: Frame Lock → Command Queue → Event Flags
2. **Timeouts:** All queue operations have 100ms timeout
3. **No Nested Locks:** Each thread acquires at most one lock at a time
4. **Lock-Free Emergency:** Emergency stop uses lock-free event flag

### Rationale

1. **Safety First:** Motor control and safety at equal highest priority ensures safety commands execute immediately
2. **Video Processing Critical:** Second tier priority ensures control loop stays fed with data
3. **Web Server Non-Critical:** Lowest priority acceptable - UI latency matters less than safety
4. **Stop Button Direct:** Web stop button → Safety Monitor ensures emergency stop isn't delayed by web server backlog

### Implementation Notes

**Python Threading Limitations:**
- Python GIL prevents true parallel execution
- Priorities implemented via queue priorities and careful design
- Real-time guarantees not possible in Python
- Use `time.sleep()` carefully to allow GIL switching

**Monitoring:**
- Log thread health every 10 seconds
- Detect deadlocks: threads not progressing >5 seconds
- Emergency recovery: Full system reset on deadlock

### Consequences

**Positive:**
- Clear thread responsibilities
- Safety-first architecture
- Predictable behavior
- Well-defined communication patterns

**Negative:**
- More complex than single-threaded
- Debugging multi-threading issues
- Need thread monitoring code
- Python GIL limits true parallelism

### Alternatives Considered

**Option A: Single-threaded asyncio (rejected)**
- Wouldn't handle blocking I2C calls well
- More complex code restructure
- Existing code is threaded

**Option B: All equal priority (rejected)**
- Safety not guaranteed
- No predictable behavior under load
- Emergency stop could be delayed

---

## ADR-009: Safety System Architecture

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-07
**Decision Date:** 2025-12-07
**Deciders:** Project Lead
**Priority:** P0 - Blocker

### Context

Safety requirements were listed but integration architecture was undefined. Critical questions:
- Where do safety checks execute?
- How does emergency stop propagate?
- What is the recovery procedure?
- Different requirements for manual vs. autonomous modes

### Decision

**ACCEPTED: Multi-Layer Safety Architecture with Mode-Dependent Behavior**

### Safety Layers

**Layer 1: Hardware (ThunderBorg Board)**
- **Failsafe:** Motors off if no command within 250ms
- **Fault Detection:** Motor overcurrent detection (built-in)
- **Activation:** Enabled via `TB.SetCommsFailsafe(True)` at startup
- **Recovery:** Automatic on next valid command

**Layer 2: Watchdog Thread (monsterWeb.py)**
- **Timeout:** 1 second of no web activity
- **Action:** Calls `TB.MotorsOff()`, sets LED to blue
- **Recovery:** Automatic reconnection resets watchdog
- **Thread:** Existing Watchdog class (independent thread)

**Layer 3: Safety Monitor Thread (New - High Priority)**
- **Responsibilities:**
  - Battery voltage monitoring
  - Drive fault checking
  - Process emergency stop signals
  - Mode-dependent safety enforcement
- **Polling Rate:** 10 Hz (100ms intervals)
- **Priority:** Equal highest with Motor Control

### Mode-Dependent Safety

**Manual Mode (Driver Controlled):**
- **Primary Safety:** Driver responsibility
- **Automatic Stops:**
  - Communication timeout (Watchdog: 1 second)
  - Hardware failsafe (ThunderBorg: 250ms)
  - Emergency stop button (web UI or hardware)
- **Speed Limiting:** FPS-based (15fps→50%, 30fps→100%)
- **Battery Warning:** Display warning, don't stop
- **Motor Faults:** Display warning, don't stop (driver decides)

**Autonomous Mode (Self-Drive):**
- **Enhanced Safety:** All checks mandatory
- **Automatic Stops:**
  - Low battery (stop and alert)
  - Motor faults (immediate stop)
  - Obstacle detection (when implemented - Phase 3)
  - Tracking loss (stop until reacquired)
  - Tilt detection (if IMU present - Phase 5)
- **Speed Limiting:** Additional limits based on obstacles/confidence
- **Recovery:** Requires manual intervention after auto-stop

### Safety Check Implementation

**Location:** Dedicated Safety Monitor Thread

**Execution Pattern:**
```python
while not terminated:
    # Check battery
    battery_voltage = TB.GetBatteryReading()
    if mode == AUTONOMOUS and battery_voltage < BATTERY_MIN:
        trigger_emergency_stop("Low battery")
    elif battery_voltage < BATTERY_WARNING:
        send_warning("Low battery")

    # Check motor faults
    fault1 = TB.GetDriveFault1()
    fault2 = TB.GetDriveFault2()
    if mode == AUTONOMOUS and (fault1 or fault2):
        trigger_emergency_stop("Motor fault")
    elif fault1 or fault2:
        send_warning("Motor fault detected")

    # Check emergency stop flag
    if emergency_stop_event.is_set():
        TB.MotorsOff()
        # ... handle emergency state

    time.sleep(0.1)  # 10 Hz polling
```

### Emergency Stop Propagation

**Trigger Sources:**
1. Web UI stop button → Sets `emergency_stop_event`
2. Hardware button (future) → GPIO interrupt → Sets `emergency_stop_event`
3. Safety Monitor checks → Sets `emergency_stop_event`
4. Watchdog timeout → Directly calls `TB.MotorsOff()`

**Propagation Mechanism:**
- **Signal:** `threading.Event()` - lock-free, fast
- **Handler:** Safety Monitor Thread
- **Action:** `TB.MotorsOff()` within 100ms
- **LED Indication:** Red LED on emergency stop

**ANY user can trigger emergency stop** (multi-user safety requirement)

### Recovery Procedures

**From Communication Timeout:**
- **Automatic:** Reconnection resets watchdog
- **Manual:** None required
- **Validation:** Watchdog automatically clears on activity

**From Emergency Stop:**
1. **Clear Condition:** Resolve cause (charge battery, check wiring, etc.)
2. **User Confirmation:** Click "Reset Emergency Stop" button
3. **System Check:** Safety Monitor validates:
   - Battery voltage acceptable
   - No motor faults
   - Communication active
4. **Clear Flag:** `emergency_stop_event.clear()`
5. **Visual Feedback:** LED returns to normal

**From Motor Fault:**
- **Manual Mode:** Warning only, driver can continue or stop
- **Autonomous Mode:** Stop required, manual reset needed
- **Validation:** Fault must clear before reset allowed

### Battery Thresholds

**To be configured in Settings:**
```python
BATTERY_MIN = 10.5V      # Autonomous stop threshold
BATTERY_WARNING = 11.0V  # Warning threshold (manual mode)
BATTERY_MAX = 12.6V      # Fully charged reference
```

### Rationale

1. **Defense in Depth:** Multiple independent safety layers
2. **Hardware Failsafe:** Ultimate protection against software bugs
3. **Mode Appropriate:** Manual mode trusts driver, autonomous mode strict
4. **Fast Emergency Stop:** Event-based, <100ms response time
5. **Existing Code Leverage:** Uses ThunderBorg built-in safety features
6. **User Empowerment:** ANY user can emergency stop (safety critical)

### Implementation Priority

**Phase 1 (Immediate):**
- [ ] Enable ThunderBorg hardware failsafe at startup
- [ ] Ensure watchdog timeout working (already implemented)
- [ ] Add web UI emergency stop button to Safety Monitor
- [ ] Implement FPS-based speed limiting

**Phase 2-4 (Autonomous Features):**
- [ ] Implement Safety Monitor Thread
- [ ] Add battery monitoring
- [ ] Add motor fault monitoring
- [ ] Implement mode switching (manual/autonomous)
- [ ] Add recovery UI

**Phase 3+ (Enhanced):**
- [ ] Obstacle detection integration
- [ ] Tilt detection (if IMU)
- [ ] Hardware emergency stop button

### Consequences

**Positive:**
- Multiple independent safety layers
- Fast emergency response
- Mode-appropriate safety
- Uses existing hardware features
- Clear recovery process

**Negative:**
- More complex than single safety check
- Mode switching logic needed
- Recovery UI needed
- Battery thresholds need calibration

### Alternatives Considered

**Option A: Single safety check in motor control (rejected)**
- Too slow - motor control busy with commands
- No independent safety monitoring
- Single point of failure

**Option B: Same safety for all modes (rejected)**
- Too restrictive for manual mode
- Driver can't override warnings
- Poor user experience

**Option C: No automatic stops in manual mode (rejected)**
- Unsafe - battery drain could damage hardware
- Communication loss must stop robot
- Doesn't meet safety requirements

---

## ADR-010: GPIO Pin Assignments

**Status:** 🟢 ACCEPTED
**Date:** 2025-12-07
**Decision Date:** 2025-12-07
**Deciders:** Project Lead
**Priority:** P0 - Blocker

### Context

GPIO pin assignments were completely missing from documentation. This created uncertainty about:
- Available pins for future expansion
- Pin conflicts
- Hardware setup instructions

**Critical Finding:** MonsterBorg is a fully built machine with ThunderBorg HAT. No additional GPIO hardware is being added at this time.

### Decision

**ACCEPTED: Document ThunderBorg HAT Pin Usage, Reserve Remaining Pins for Future**

### Current Pin Assignments (ThunderBorg HAT)

**I2C Bus (Used by ThunderBorg):**

| Pin Function | BCM Pin | Physical Pin | Usage |
|--------------|---------|--------------|-------|
| I2C1 SDA | GPIO 2 | Pin 3 | ThunderBorg communication |
| I2C1 SCL | GPIO 3 | Pin 5 | ThunderBorg communication |

**I2C Device Address:**
- ThunderBorg: `0x15` (default, configurable)

**Power Pins (Used by HAT):**
- 3.3V Power: Pin 1
- 5V Power: Pin 2, Pin 4
- Ground: Pin 6, Pin 9, Pin 14, Pin 20, Pin 25, Pin 30, Pin 34, Pin 39

**Note:** ThunderBorg is a HAT (Hardware Attached on Top) that sits on all 40 GPIO pins but only actively uses I2C pins 2 and 3.

### Available GPIO Pins (For Future Expansion)

All GPIO pins except 2 and 3 are available for future use:

**Recommended for Future Phases:**

#### Phase 3: Obstacle Detection
- **Ultrasonic Sensor 1:** Trigger GPIO 23, Echo GPIO 24
- **Ultrasonic Sensor 2:** Trigger GPIO 27, Echo GPIO 22
- **Ultrasonic Sensor 3:** Trigger GPIO 17, Echo GPIO 18

#### Phase 1+: Hardware Emergency Stop
- **Emergency Button:** GPIO 21 (pull-up, active low)

#### Phase 1+: Status LEDs (if not using ThunderBorg onboard LEDs)
- **Power LED:** GPIO 16 (green)
- **Status LED:** GPIO 20 (blue)
- **Error LED:** GPIO 26 (red)

#### Phase 5: IMU (if added)
- **I2C Address:** 0x68 or 0x69 (typical MPU-6050/9250)
- **Uses same I2C bus:** GPIO 2/3 (shared with ThunderBorg)

#### Phase 5: Wheel Encoders (if added)
- **Left Encoder:** GPIO 5, GPIO 6
- **Right Encoder:** GPIO 13, GPIO 19

### Pin Reservation Strategy

**Do NOT Use (Reserved for HAT):**
- GPIO 2, 3 (I2C - actively used)
- All power and ground pins

**Recommended to Avoid (SPI/Special Functions):**
- GPIO 7-11 (SPI0 - conflicts with HAT if needed)
- GPIO 14, 15 (UART - used for console)

**Safe to Use:**
- GPIO 4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27

### ThunderBorg Onboard Features (No GPIO Required)

**ThunderBorg provides via I2C (no additional GPIO needed):**
- 2x Motor outputs
- 2x RGB LEDs (onboard, I2C controlled)
- Battery voltage monitoring
- Motor fault detection
- Communications failsafe

**Use ThunderBorg LEDs instead of external GPIO LEDs:**
- `TB.SetLed1(r, g, b)` - ThunderBorg onboard LED
- `TB.SetLed2(r, g, b)` - ThunderBorg lid LED
- No GPIO pins required!

### Voltage Level Considerations

**ThunderBorg I2C:** 3.3V logic (Raspberry Pi native)

**Future Sensor Considerations:**
- **Ultrasonic sensors (HC-SR04):** 5V logic on echo pin
  - **CRITICAL:** Requires voltage divider (5V → 3.3V) on echo pins
  - Trigger pin: Direct connection (Pi 3.3V is sufficient)
  - Echo pin: Voltage divider required (10kΩ + 20kΩ recommended)

### Rationale

1. **No Additional Hardware:** MonsterBorg fully built, no GPIO needed now
2. **Document Current State:** Clear understanding of what's used
3. **Plan for Future:** Reserve pins for documented future phases
4. **Avoid Conflicts:** Explicit pin reservations prevent conflicts
5. **Use Onboard LEDs:** ThunderBorg has LEDs, no GPIO LEDs needed
6. **Safety for Expansion:** Voltage divider notes prevent damage

### Implementation Actions

**Immediate (Phase 1):**
- [ ] Document current I2C usage in setup guide
- [ ] No GPIO changes needed (no additional hardware)
- [ ] Use ThunderBorg onboard LEDs for status

**Future Phases:**
- [ ] Implement pin assignments when hardware added
- [ ] Validate no conflicts before adding sensors
- [ ] Add voltage dividers for 5V sensors
- [ ] Update pin assignment table

### Consequences

**Positive:**
- Clear documentation of current usage
- Future expansion planned
- No pin conflicts
- Uses existing hardware features
- Safety notes for future additions

**Negative:**
- None - this is documentation only

### Alternatives Considered

**Option A: Assign all pins now (rejected)**
- Premature - no hardware to assign yet
- Would be speculative
- Could create conflicts later

**Option B: External GPIO LEDs now (rejected)**
- Unnecessary - ThunderBorg has onboard LEDs
- Wastes GPIO pins
- More wiring complexity

---

## Decision Review Process

### Weekly Review

- Review all 🟡 Proposed decisions
- Escalate blockers
- Update status

### Before Phase Kickoff

- All P0 decisions for that phase must be 🟢 Accepted
- Document decisions in relevant documents
- Update architecture diagrams

### Decision Amendment Process

1. Create new ADR superseding old one
2. Mark old ADR as 🔵 Superseded
3. Link to new ADR
4. Maintain history (don't delete old ADRs)

---

**Document Owner:** Project Lead
**Review Frequency:** Weekly
**Last Review:** 2025-12-06
