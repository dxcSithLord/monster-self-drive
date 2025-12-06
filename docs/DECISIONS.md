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
| ADR-001 | WebSocket Library Selection | 🟡 Proposed | 2025-12-06 | P0 |
| ADR-002 | Configuration Format | 🟡 Proposed | 2025-12-06 | P1 |
| ADR-003 | Directory Structure | 🟡 Proposed | 2025-12-06 | P1 |
| ADR-004 | Multi-User Control Model | 🟡 Proposed | 2025-12-06 | P0 |
| ADR-005 | Tracking Algorithm Strategy | 🟡 Proposed | 2025-12-06 | P1 |
| ADR-006 | IMU Hardware Status | 🟡 Proposed | 2025-12-06 | P3 |
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

**Status:** 🟡 PROPOSED (BLOCKER)
**Date:** 2025-12-06
**Deciders:** [To be assigned]
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

**[PENDING - To be decided]**

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

**[TEAM INPUT NEEDED]**

**Suggested Decision:** Flask-SocketIO
**Rationale:**
1. Current codebase uses Flask (easier integration)
2. Synchronous code can remain mostly unchanged
3. Automatic reconnection crucial for remote robot control
4. Latency difference (10-20ms) acceptable for driving application
5. Lower implementation risk

**Alternative:** If performance profiling shows unacceptable latency, migrate to `websockets` in Phase 2.

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

- [ ] Decision maker assigned
- [ ] Prototype both options (2-4 hours each)
- [ ] Measure actual latency on Raspberry Pi
- [ ] Team review and vote
- [ ] Update REQUIREMENTS.md with chosen library
- [ ] Update IMPLEMENTATION.md with architecture

---

## ADR-002: Configuration Format

**Status:** 🟡 PROPOSED
**Date:** 2025-12-06
**Deciders:** [To be assigned]
**Priority:** P1 - Resolve before Phase 1

### Context

Configuration is currently stored in `Settings.py` (Python module), but documentation mentions "JSON or INI". Inconsistency causes confusion and affects:
- Configuration management
- User editability
- Validation
- Deployment automation

### Decision

**[PENDING - To be decided]**

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

**Suggested Decision:** **JSON with comments extension** OR **TOML**

**Rationale:**
1. **JSON** if integration/automation is priority
2. **TOML** if user experience is priority
3. Both support validation and hierarchy
4. Both have good Python support

**Hybrid Approach:**
```python
# Support both! Load priority:
# 1. config.json (if exists)
# 2. config.toml (if exists)
# 3. Settings.py (fallback/defaults)
```

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
- Clear configuration location
- User can edit without Python knowledge
- Validation prevents errors
- Easier deployment automation

**Negative:**
- Migration effort required
- Need to document new format
- Potential for configuration errors

### Action Items

- [ ] Choose format (JSON or TOML recommended)
- [ ] Create schema definition
- [ ] Write migration script
- [ ] Update documentation
- [ ] Create example config file

---

## ADR-003: Directory Structure

**Status:** 🟡 PROPOSED
**Date:** 2025-12-06
**Deciders:** [To be assigned]
**Priority:** P1 - Resolve before Phase 1

### Context

Current codebase has flat structure in root directory. CONSTITUTION proposes `src/` based structure. Need to decide:
- Migrate to src/ structure OR keep flat
- When to migrate (before or during development)
- Import path changes

### Current Structure

```
monster-self-drive/
├── ImageProcessor.py
├── MonsterAuto.py
├── Settings.py
├── ThunderBorg.py
└── monsterWeb.py
```

### Proposed Structure (from CONSTITUTION)

```
monster-self-drive/
└── src/
    ├── core/
    │   ├── __init__.py
    │   └── monster_auto.py
    ├── web/
    │   ├── __init__.py
    │   └── web_server.py
    ├── vision/
    │   ├── __init__.py
    │   └── image_processor.py
    └── hardware/
        ├── __init__.py
        └── thunderborg.py
```

### Decision

**[PENDING - To be decided]**

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

**Suggested Decision:** **Migrate to src/ structure BEFORE Phase 1**

**Rationale:**
1. Project will grow (6+ modules planned)
2. Better to migrate early (less code to change)
3. Clearer organization helps new contributors
4. Testing benefits from src/ separation

### Migration Plan

```bash
# Step 1: Create structure
mkdir -p src/{core,web,vision,hardware,utils}

# Step 2: Move files
mv MonsterAuto.py src/core/monster_auto.py
mv monsterWeb.py src/web/web_server.py
mv ImageProcessor.py src/vision/image_processor.py
mv ThunderBorg.py src/hardware/thunderborg.py
mv Settings.py src/core/settings.py

# Step 3: Add __init__.py files
touch src/__init__.py
touch src/{core,web,vision,hardware,utils}/__init__.py

# Step 4: Update imports in all files

# Step 5: Update README and documentation
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

- [ ] Approve migration decision
- [ ] Create migration script
- [ ] Update all imports
- [ ] Update documentation
- [ ] Test all modules after migration

---

## ADR-004: Multi-User Control Model

**Status:** 🟡 PROPOSED (SAFETY CRITICAL)
**Date:** 2025-12-06
**Deciders:** [To be assigned]
**Priority:** P0 - Safety blocker

### Context

REQUIREMENTS specify "3 simultaneous connections" but don't define control arbitration. Critical safety issue:
- What happens when multiple users send conflicting commands?
- Who has control of the robot?
- How to prevent dangerous situations?

### Decision

**[PENDING - To be decided]**

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

**Suggested Decision:** **Option 1 - Single Active User**

**Additional Safety Rules:**
1. **Emergency Stop:** ANY user can trigger (broadcasts to all)
2. **Observer Mode:** Non-active users see video but UI disabled
3. **Control Request:** Queue system for requesting control
4. **Timeout:** Auto-release control after 5 min inactivity
5. **Indicator:** Large UI banner showing who has control

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

- [ ] Approve control model
- [ ] Design UI mockups
- [ ] Implement ControlManager class
- [ ] Add control indicators to web UI
- [ ] Test control handoff scenarios
- [ ] Document in user guide

---

## ADR-005: Tracking Algorithm Strategy

**Status:** 🟡 PROPOSED
**Date:** 2025-12-06
**Priority:** P1 - Needed before Phase 2

### Context

Multiple tracking algorithms mentioned (KCF, CSRT, MOSSE, Template, Color) but no clear strategy for which to implement when.

### Decision

**[PENDING - To be decided]**

### Proposed Strategy

**Phase 2 MVP:** Single algorithm (CSRT recommended)
**Phase 3:** Add fallback (MOSSE for speed)
**Phase 4:** True hybrid with algorithm selection

**Rationale:** Start simple, add complexity as needed

### Action Items

- [ ] Prototype CSRT performance on Raspberry Pi
- [ ] Document algorithm selection in IMPLEMENTATION.md

**Note:** Detailed analysis deferred until Phase 2 planning

---

## ADR-006 through ADR-010: Placeholder

**Status:** 🟡 PROPOSED

Remaining ADRs outlined in CRITICAL_GAPS.md:
- ADR-006: IMU Hardware Status
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
