# Critical Gaps and Missing Specifications

**Status:** Requires Resolution Before Implementation
**Last Updated:** 2025-12-06
**Priority:** BLOCKER

This document identifies critical gaps, inconsistencies, and missing
specifications discovered across the project documentation (REQUIREMENTS,
CONSTITUTION, IMPLEMENTATION). These must be resolved before proceeding with
development.

---

## 🚨 Critical Gaps (Must Decide Before Starting)

### 1. WebSocket Library Choice (Phase 1 Blocker)

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-06
**Impact:** Completely different architectures, threading models
**Affected Phases:** Phase 1

**Problem:** (RESOLVED)

- Documentation mentions both `websockets` and `Flask-SocketIO`
- No decision on which library to use
- Each choice leads to fundamentally different architectures

**RESOLUTION:**
**Decision: Flask-SocketIO** (See ADR-001 in DECISIONS.md)

**Rationale:**

1. Integrates with existing Flask framework in `monsterWeb.py`
2. Performance adequate for single-user control model (20-30ms latency acceptable)
3. Automatic reconnection crucial for remote robot control
4. Lower migration risk (synchronous code remains mostly unchanged)
5. Rich client-side library ecosystem

**Implementation:**

- Library: Flask-SocketIO >= 3.0
- Async mode: Start with threading mode
- Client-side: socket.io-client for JavaScript

**Completed Actions:**

- [x] Choose one library and document rationale - Flask-SocketIO selected
- [x] Decision documented in ADR-001
- [ ] Update requirements.txt with Flask-SocketIO
- [ ] Update IMPLEMENTATION_PLAN.md with architecture details
- [ ] Implement in monsterWeb.py (Phase 1)

**Reference:** See `docs/DECISIONS.md` ADR-001 for complete analysis

---

### 2. Configuration Format Inconsistency (Affects All Phases)

**Status:** ⚠️ INCONSISTENT
**Impact:** Developer confusion, documentation mismatch
**Affected Phases:** All

**Inconsistencies Found:**

| Document | Specified Format | Location |
| --------- | ---------------------- | ----------------------- |
| REQUIREMENTS | "JSON or INI" | Configuration section |
| Current Code | `Settings.py` (Python module) | Root directory |
| IMPLEMENTATION | Python format | Configuration examples |

**Problem:**

- No single source of truth for configuration format
- Migration path unclear if format changes
- Validation/schema undefined

**Required Decisions:**

- [ ] Choose ONE format: JSON, INI, or Python module
- [ ] Document migration plan if changing from current `Settings.py`
- [ ] Define configuration schema/validation
- [ ] Update all documentation to match
- [ ] Specify configuration file location (root vs. config directory)

**Current State:** Using `Settings.py` (Python module)

---

### 3. Directory Structure Migration (Phase 1 Blocker)

**Status:** ⚠️ UNDEFINED
**Impact:** Code organization, import paths, deployment
**Affected Phases:** Phase 1 and beyond

**Current State:**

```text
monster-self-drive/
├── ImageProcessor.py
├── MonsterAuto.py
├── Settings.py
├── ThunderBorg.py
└── monsterWeb.py
```

**Proposed State (from CONSTITUTION):**

```text
monster-self-drive/
└── src/
    ├── core/
    ├── web/
    ├── vision/
    └── hardware/
```

**Gaps:**

- No migration plan documented
- Import path changes not addressed
- Backwards compatibility not considered
- Deployment impact not analyzed

**Required Decisions:**

- [ ] Decide: Migrate to `src/` structure OR keep flat structure
- [ ] If migrating: Define migration timeline (before Phase 1 or during?)
- [ ] Document import path changes
- [ ] Update all import statements in documentation
- [ ] Consider symlinks for backwards compatibility
- [ ] Update deployment scripts

---

### 4. Tracking Algorithm Priority (Phase 2 Blocker)

**Status:** ⚠️ AMBIGUOUS
**Impact:** Feature implementation order, performance expectations
**Affected Phases:** Phase 2

**Listed Algorithms:**

1. KCF (Kernelized Correlation Filter)
2. CSRT (Channel and Spatial Reliability Tracker)
3. MOSSE (Minimum Output Sum of Squared Error)
4. Template Matching
5. Color-based tracking

**Current Specification:** "Hybrid approach" (undefined)

**Gaps:**

- Which algorithm for MVP?
- What does "hybrid" mean exactly?
- Fallback order not specified
- Performance requirements per algorithm missing
- Algorithm selection criteria undefined

**Required Decisions:**

- [ ] Define MVP algorithm (single algorithm for Phase 2)
- [ ] Specify "hybrid approach" in detail:
  - Which algorithms run in parallel?
  - How are results combined?
  - Confidence scoring mechanism
- [ ] Define fallback order: Primary → Secondary → Tertiary
- [ ] Set performance thresholds for algorithm switching
- [ ] Document when each algorithm is appropriate

**Recommendation:**
Start with single algorithm (CSRT or KCF), add hybrid in later phase

---

### 5. Multi-User Behavior (Phase 1 Safety Issue)

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-06
**Impact:** Physical safety, robot control conflicts
**Affected Phases:** Phase 1

**Problem:** (RESOLVED)

- REQUIREMENTS mentions "3 simultaneous connections"
- **NOT SPECIFIED:** Who has control when multiple users connected

**RESOLUTION:**
**Decision: Single Active User Model** (See ADR-004 in DECISIONS.md)

**Control Model:**

1. **One Active User:** Only ONE user has active control at any time
2. **Observer Mode:** Other connected users see video feed only (controls disabled)
3. **Control Handoff:**
   - Second user can request to take over control
   - Second user automatically gains access when first user disconnects
   - Optional: Active user can voluntarily release control
4. **Emergency Stop:** ANY connected user can trigger emergency stop
   (CRITICAL SAFETY FEATURE)

**Safety Scenarios Resolved:**

- ✅ User A drives forward, User B drives backward simultaneously →
  **B has no control, command ignored**
- ✅ User A in autonomous mode, User B switches to manual →
  **B must request control first**
- ✅ User A has control, User B presses emergency stop →
  **Emergency stop activates for ANY user**

**Completed Actions:**

- [x] Define control arbitration model - Single Active User
- [x] Specify command priority rules - Only active user's commands executed
- [x] Define emergency stop behavior - ANY user can trigger
- [x] Define control handoff mechanisms
- [ ] Implement ControlManager class in monsterWeb.py
- [ ] Design UI mockups for active/observer modes
- [ ] Add UI indicators showing who has control
- [ ] Update REQUIREMENTS.md with control model specification

**Reference:** See `docs/DECISIONS.md` ADR-004 for complete analysis

**Safety Requirement:** ✅ RESOLVED before Phase 1 implementation

---

### 6. IMU Status Confusion (Phase 5 Blocker)

**Status:** ⚠️ CONFLICTING
**Impact:** Hardware requirements, budget, fallback behavior
**Affected Phases:** Phase 5

**Conflicting Specifications:**

| Document | IMU Status | Implication |
| --------- | -------------------------------- | ----------------------- |
| REQUIREMENTS | "Recommended Additional Hardware" | Optional component |
| CONSTITUTION | "Integrated module" | Required component |
| IMPLEMENTATION | "Source and install IMU" | Required for Phase 5 |

**Gaps:**

- Is IMU required or optional?
- What happens if IMU not present?
- Fallback odometry methods undefined
- Calibration requirements unclear

**Required Decisions:**

- [ ] Clarify: Required vs. Optional vs. Recommended
- [ ] If optional: Define fallback behavior without IMU
- [ ] If required: Update REQUIREMENTS to reflect this
- [ ] Specify IMU model/interface (I2C? SPI?)
- [ ] Define calibration procedure
- [ ] Document degraded operation mode without IMU

**Impact on Phases:**

- If required: Must be specified in Phase 1 hardware setup
- If optional: Need graceful degradation strategy

---

## ⚠️ Major Missing Specifications

### 7. GPIO Pin Assignments

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-07
**Impact:** Hardware integration, pin conflicts
**Affected Phases:** Phase 1, 3, 5

**RESOLUTION:**
**Decision: Document ThunderBorg HAT, Reserve Pins for Future** (See ADR-010 in DECISIONS.md)

**Critical Finding:** MonsterBorg is fully built with ThunderBorg HAT attached. No additional GPIO hardware is being added at this time.

**Current Pin Usage:**

#### I2C Bus (ThunderBorg HAT)

- **I2C1 SDA:** GPIO 2 (Pin 3)
- **I2C1 SCL:** GPIO 3 (Pin 5)
- **I2C Address:** 0x15 (ThunderBorg)

**ThunderBorg Onboard Features (No GPIO Required):**

- 2x Motor outputs
- 2x RGB LEDs (onboard, I2C controlled via `TB.SetLed1()`, `TB.SetLed2()`)
- Battery voltage monitoring
- Motor fault detection
- Communications failsafe

**Key Insight:** Use ThunderBorg onboard LEDs instead of external GPIO LEDs - saves GPIO pins!

**Future Pin Reservations (Documented):**

- Phase 3 (Ultrasonic): GPIO 17, 18, 22, 23, 24, 27
- Phase 1+ (Emergency button): GPIO 21
- Phase 5 (Encoders): GPIO 5, 6, 13, 19
- Phase 5 (IMU): Shares I2C bus with ThunderBorg

**Completed Actions:**

- [x] Document ThunderBorg I2C pin usage
- [x] Identify all available GPIO pins
- [x] Reserve pins for future phases
- [x] Document voltage divider requirements for 5V sensors
- [x] Note ThunderBorg onboard LED usage
- [ ] Create hardware setup guide

**Reference:** See `docs/DECISIONS.md` ADR-010 for complete pin assignments

---

### 8. Calibration Procedures

**Status:** ⚠️ MENTIONED BUT UNDEFINED
**Impact:** Accuracy, user experience, system reliability
**Affected Phases:** Phase 1, 5

**Current State:** Mentioned in requirements but no procedures defined

#### Distance Calibration (Phase 1)

**Missing:**

- [ ] Step-by-step user procedure
- [ ] UI/UX flow (web wizard? CLI tool?)
- [ ] Calibration data format and storage location
- [ ] Validation criteria (how to verify calibration success?)
- [ ] Recalibration triggers (when needed?)

**Example Needed:**

```text
1. User places robot 50cm from wall
2. User clicks "Calibrate Distance" in web UI
3. System takes 10 measurements
4. System calculates correction factor
5. System validates measurement variance
6. System saves calibration to config
```

#### Odometry Calibration (Phase 5)

**Missing:**

- [ ] Measurement procedure (straight line? square pattern?)
- [ ] Required measurement distance/accuracy
- [ ] Wheel circumference calculation method
- [ ] Drift correction procedure
- [ ] Storage format for calibration constants

#### IMU Calibration

**Status:** Not mentioned at all

**Required if IMU used:**

- [ ] Magnetometer calibration (hard/soft iron)
- [ ] Accelerometer calibration
- [ ] Gyroscope bias calibration
- [ ] Calibration procedure (figure-8 motion?)
- [ ] Validation tests

**Required Actions:**

- [ ] Document complete calibration workflow for each sensor
- [ ] Create web UI mockups for calibration wizards
- [ ] Define calibration data schema
- [ ] Specify validation criteria
- [ ] Add calibration state to system status

---

### 9. Threading Model Details

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-07
**Impact:** System stability, deadlocks, race conditions
**Affected Phases:** Phase 1, 2, 4

**RESOLUTION:**
**Decision: Priority-Based Threading with Safety-First Architecture** (See ADR-008 in DECISIONS.md)

**Thread Priority Hierarchy:**

**Tier 1 (Highest - Equal Priority):**

- Motor Control Thread
- Safety Monitor Thread

**Tier 2 (Medium Priority):**

- Video Streaming Thread
- Image Processing Thread

**Tier 3 (Lowest Priority):**

- Web Server Thread

**Critical Linkage:** Web server stop button directly signals Safety Monitor Thread

**Inter-Thread Communication:**

- **Control Command Queue:** `queue.Queue(maxsize=10)` - Image Processing & Web Server → Motor Control
- **Safety Event Flags:** `threading.Event()` - Emergency stop, battery low, comm timeout
- **Frame Buffer:** Circular buffer (2 frames) with `threading.Lock()` - Video → Image Processing & Web Server

**Deadlock Prevention:**

1. Lock ordering: Frame Lock → Command Queue → Event Flags
2. All queue operations have 100ms timeout
3. No nested locks (max one lock per thread at a time)
4. Emergency stop uses lock-free event flag

**Completed Actions:**

- [x] Define thread priority hierarchy
- [x] Specify inter-thread communication patterns
- [x] Define deadlock prevention rules
- [x] Document monitoring requirements
- [ ] Create threading architecture diagram
- [ ] Implement Motor Control Thread
- [ ] Implement Safety Monitor Thread
- [ ] Add thread health monitoring

**Reference:** See `docs/DECISIONS.md` ADR-008 for complete threading architecture

---

### 10. Safety System Integration

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-07
**Impact:** Physical safety, system reliability
**Affected Phases:** All (safety-critical)

**RESOLUTION:**
**Decision: Multi-Layer Safety Architecture with Mode-Dependent Behavior** (See ADR-009 in DECISIONS.md)

**Safety Layers:**

**Layer 1: Hardware (ThunderBorg Board)**

- Failsafe: Motors off if no command within 250ms
- Fault detection: Motor overcurrent detection (built-in)
- Activation: Enabled via `TB.SetCommsFailsafe(True)` at startup

**Layer 2: Watchdog Thread (monsterWeb.py)**

- Timeout: 1 second of no web activity
- Action: Calls `TB.MotorsOff()`, sets LED to blue
- Recovery: Automatic reconnection resets watchdog

**Layer 3: Safety Monitor Thread (New - High Priority)**

- Battery voltage monitoring
- Drive fault checking
- Process emergency stop signals
- Mode-dependent safety enforcement
- Polling Rate: 10 Hz (100ms intervals)

**Mode-Dependent Safety:**

**Manual Mode:**

- Primary safety: Driver responsibility
- Automatic stops: Communication timeout, hardware failsafe, emergency button
- Speed limiting: FPS-based (15fps→50%, 30fps→100%)
- Warnings only: Battery low, motor faults (driver decides)

**Autonomous Mode:**

- Enhanced safety: All checks mandatory
- Automatic stops: Low battery, motor faults, obstacle detection, tracking loss
- Speed limiting: Additional limits based on obstacles/confidence
- Recovery: Requires manual intervention

**Emergency Stop Propagation:**

- Trigger sources: Web UI, hardware button (future), safety checks, watchdog
- Mechanism: `threading.Event()` - lock-free, fast
- Response time: <100ms
- ANY user can trigger emergency stop

**Completed Actions:**

- [x] Design multi-layer safety architecture
- [x] Define mode-dependent behavior (manual vs autonomous)
- [x] Specify emergency stop propagation mechanism
- [x] Document recovery procedures
- [x] Leverage existing ThunderBorg safety features
- [ ] Implement Safety Monitor Thread
- [ ] Add battery monitoring thresholds to Settings
- [ ] Create recovery UI
- [ ] Add safety system to architecture diagrams

**Reference:** See `docs/DECISIONS.md` ADR-009 for complete safety architecture

---

### 11. Frame Rate Conflict

**Status:** ✅ RESOLVED
**Resolution Date:** 2025-12-07
**Impact:** System performance expectations, hardware selection
**Affected Phases:** Phase 1, 2

**RESOLUTION:**
**Decision: Adaptive Frame Rate with Speed Limiting** (See ADR-007 in DECISIONS.md)

**Accepted Frame Rate Tiers:**

- **Minimum:** 15 fps → Maximum robot speed limited to 50%
- **Target:** 30 fps → 100% maximum speed available
- **Above Target:** >30 fps → No additional speed benefit

**Policy:** Quality over frame rate - skip frames if needed to maintain processing quality

**Rationale:**

1. Current Raspberry Pi + Camera V2 achieves 30fps with OpenCV color following
2. Safety first: Lower frame rates = lower max speed ensures safety
3. Processing priority: Better to process fewer frames well than many frames poorly
4. Graceful degradation: System remains functional at lower frame rates

**Completed Actions:**

- [x] Define FPS tiers and speed limiting logic
- [x] Specify frame skip policy (quality over quantity)
- [x] Document in ADR-007
- [ ] Implement FPS monitoring
- [ ] Implement speed limiting based on FPS
- [ ] Add low FPS warning UI

**Reference:** See `docs/DECISIONS.md` ADR-007 for complete analysis

---

## 📋 Missing Procedures

### 12. Calibration UI/Workflows

**Status:** ⚠️ NO USER INTERFACE DEFINED
**Impact:** User experience, system accuracy
**Affected Phases:** Phase 1, 5

**Missing Specifications:**

#### UI Method

How does user perform calibrations?

- [ ] Web interface wizard (step-by-step)
- [ ] CLI tool (command-line)
- [ ] Manual JSON/config file editing
- [ ] Combination of above

#### Workflow Examples Needed

**Distance Calibration Workflow:**

```text
[UNDEFINED - Need to specify:
 - UI mockup
 - Step-by-step instructions
 - Visual feedback
 - Error handling
 - Success confirmation]
```

**Odometry Calibration Workflow:**

```text
[UNDEFINED - Need to specify:
 - Measurement procedure UI
 - Real-time feedback
 - Calculation display
 - Validation steps]
```

#### Validation Procedures

- [ ] How does user know calibration succeeded?
- [ ] Visual indicators (green checkmark? percentage?)
- [ ] Measurement comparison (expected vs. actual)
- [ ] Recalibration triggers (out of spec?)

**Required Actions:**

- [ ] Create UI mockups for each calibration type
- [ ] Document step-by-step user procedures
- [ ] Define validation criteria and feedback
- [ ] Add calibration status to web UI
- [ ] Create calibration troubleshooting guide

---

### 13. Hardware Setup Guide

**Status:** ⚠️ LISTS HARDWARE, MISSING SETUP DETAILS
**Impact:** First-time setup experience, troubleshooting
**Affected Phases:** Phase 1

**Current State:** Hardware components listed in REQUIREMENTS

**Missing Documentation:**

#### Connection Diagrams

- [ ] Wiring diagram for ThunderBorg to Pi
- [ ] Camera connection diagram
- [ ] Ultrasonic sensor wiring (including voltage divider if needed)
- [ ] Emergency stop button wiring
- [ ] Power distribution diagram
- [ ] Complete system diagram

#### Power Budget

- [ ] Raspberry Pi power consumption
- [ ] ThunderBorg + motors power consumption
- [ ] Camera power consumption
- [ ] Sensor power consumption
- [ ] Total current requirements
- [ ] Battery capacity requirements
- [ ] Runtime calculations

#### Hardware Detection

- [ ] How to verify ThunderBorg is detected
- [ ] I2C detection commands (`i2cdetect -y 1`)
- [ ] Camera detection (`vcgencmd get_camera`)
- [ ] GPIO verification procedures

#### Troubleshooting Guide

- [ ] ThunderBorg not detected (I2C issues)
- [ ] Camera not working
- [ ] GPIO permissions
- [ ] Power issues
- [ ] Motor not responding

**Required Actions:**

- [ ] Create detailed wiring diagrams
- [ ] Calculate and document power budget
- [ ] Write hardware verification procedures
- [ ] Create troubleshooting flowcharts
- [ ] Add hardware checklist to setup guide

---

### 14. Deployment & Installation

**Status:** ⚠️ BASIC STEPS ONLY
**Impact:** Production readiness, security
**Affected Phases:** Phase 1 and beyond

**Current Documentation:** Basic installation steps

**Missing Critical Information:**

#### Network Security

- [ ] Authentication mechanism (basic auth? token? OAuth?)
- [ ] HTTPS setup procedure (Let's Encrypt? self-signed?)
- [ ] Certificate management
- [ ] WebSocket security (wss://)
- [ ] Password/token storage (how? where?)

#### Firewall Configuration

- [ ] Required ports to open
- [ ] iptables rules example
- [ ] UFW configuration example
- [ ] Port forwarding for remote access

#### Remote Access

- [ ] VPN setup (recommended method)
- [ ] Dynamic DNS configuration
- [ ] Port forwarding security considerations
- [ ] Reverse proxy setup (nginx?)

#### Backup & Restore

- [ ] What to backup:
  - Configuration files
  - Calibration data
  - User settings
- [ ] Backup procedure
- [ ] Restore procedure
- [ ] Configuration export/import

#### Auto-Start Configuration

- [ ] systemd service file example
- [ ] Auto-start on boot
- [ ] Automatic restart on failure
- [ ] Logging configuration

**Required Actions:**

- [ ] Create security hardening guide
- [ ] Document network setup procedures
- [ ] Write backup/restore procedures
- [ ] Create systemd service file
- [ ] Add deployment checklist

---

## 🔄 Cross-Document Inconsistencies

### Summary Table

| Issue | REQUIREMENTS | CONSTITUTION | IMPLEMENTATION | Resolution Needed |
| ---- | ---- | ---- | ---- | ---- |
| **Config Format** | JSON/INI | Unspecified | Settings.py | Choose format |
| **Directory** | Unmentioned | `src/` | Unmentioned | Migrate or stay |
| **Type Hints** | Recommended | Required | Unmentioned | Clarify requirement |
| **IMU Status** | Optional | Required | Required | Clarify status |
| **Tracking Algo** | 4 types | Unspecified | 5 types | Define MVP |
| **WebSocket Lib** | Both | Unspecified | Unspecified | Choose library |
| **Frame Rate** | 30 fps min | Unspecified | ~15 fps | Define rates |
| **Multi-User** | 3 connections | Unspecified | Unspecified | Define control |
| **Safety** | Listed | Unspecified | Unspecified | Define arch |

---

## 📊 Priority Matrix

### P0 - Blockers (Must Resolve Immediately) - ✅ ALL RESOLVED

1. ✅ **WebSocket Library Choice** - RESOLVED: Flask-SocketIO (ADR-001)
2. ✅ **Multi-User Behavior** - RESOLVED: Single Active User Model (ADR-004)
3. ✅ **GPIO Pin Assignments** - RESOLVED: ThunderBorg HAT documented (ADR-010)
4. ✅ **Safety System Integration** - RESOLVED: Multi-Layer Safety Architecture (ADR-009)

### P1 - High Priority (Resolve Before Implementation) - ✅ ALL RESOLVED

1. ✅ **Configuration Format** - RESOLVED: JSON with Python Wrapper (ADR-002)
2. ✅ **Directory Structure** - RESOLVED: Structured `src/` Layout (ADR-003)
3. ✅ **Threading Model Details** - RESOLVED: Priority-Based Threading (ADR-008)
4. ✅ **Frame Rate Specification** - RESOLVED: Adaptive Frame Rate with Speed Limiting (ADR-007)

### P2 - Medium Priority (Resolve During Phase 1-2)

1. ✅ **Tracking Algorithm Priority** - RESOLVED: HSV Color-Based MVP (ADR-005)
2. **Calibration Procedures** - Needed before Phase 1 complete
3. **Hardware Setup Guide** - Needed for initial setup

### P3 - Lower Priority (Resolve Before Later Phases)

1. ✅ **IMU Status** - RESOLVED: Optional Hardware (ADR-006)
2. **Deployment & Installation** - Production concern
3. **Calibration UI/Workflows** - UX improvement

---

## ✅ Resolution Process

### For Each Gap

1. **Research & Analysis**
   - Review existing code
   - Check industry best practices
   - Evaluate options

2. **Decision Documentation**
   - Document in `DECISIONS.md`
   - Include rationale
   - Note alternatives considered

3. **Documentation Update**
   - Update affected documents
   - Ensure consistency
   - Add to relevant sections

4. **Validation**
   - Review for conflicts
   - Check completeness
   - Verify feasibility

---

## 📝 Next Steps

### Immediate Actions Required

1. **Create `DECISIONS.md`** to track architectural decisions
2. **Prioritize P0 gaps** for immediate resolution
3. **Assign owners** to each gap (if team project)
4. **Set deadlines** for gap resolution
5. **Review existing code** to understand current state
6. **Update project timeline** based on resolution time

### Documentation Improvements

- [ ] Create master glossary for consistent terminology
- [ ] Add cross-references between documents
- [ ] Create decision log for all choices
- [ ] Maintain change history for requirements

---

## 🔗 Related Documents

- [DECISIONS.md](./DECISIONS.md) - Architectural decisions
- [REQUIREMENTS.md](./REQUIREMENTS.md) - System requirements
- [PROJECT_CONSTITUTION.md](./PROJECT_CONSTITUTION.md) - Code standards
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Implementation plan
- `architecture/` - Architecture diagrams (to be created)

---

**Document Status:** Living document - update as gaps are resolved
**Review Frequency:** Before each phase kickoff
**Owner:** Project Lead
**Last Review:** 2025-12-06
