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
| ADR-007 | Frame Rate Requirements | 🟡 Proposed | 2025-12-06 | P1 |
| ADR-008 | Threading Model | 🟡 Proposed | 2025-12-06 | P1 |
| ADR-009 | Safety System Architecture | 🟡 Proposed | 2025-12-06 | P0 |
| ADR-010 | GPIO Pin Assignments | 🟡 Proposed | 2025-12-06 | P0 |

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

## ADR-007 through ADR-010: Placeholder

**Status:** 🟡 PROPOSED

Remaining ADRs outlined in CRITICAL_GAPS.md:
- ADR-007: Frame Rate Requirements
- ADR-008: Threading Model
- ADR-009: Safety System Architecture
- ADR-010: GPIO Pin Assignments

**To be detailed as decisions are made.**

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
