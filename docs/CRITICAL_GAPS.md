# Critical Gaps and Missing Specifications

**Status:** Requires Resolution Before Implementation
**Last Updated:** 2025-12-06
**Priority:** BLOCKER

This document identifies critical gaps, inconsistencies, and missing specifications discovered across the project documentation (REQUIREMENTS, CONSTITUTION, IMPLEMENTATION). These must be resolved before proceeding with development.

---

## 🚨 Critical Gaps (Must Decide Before Starting)

### 1. WebSocket Library Choice (Phase 1 Blocker)

**Status:** ⚠️ UNRESOLVED BLOCKER
**Impact:** Completely different architectures, threading models
**Affected Phases:** Phase 1

**Problem:**
- Documentation mentions both `websockets` and `Flask-SocketIO`
- No decision on which library to use
- Each choice leads to fundamentally different architectures

**Impact Analysis:**
- **websockets library:**
  - Async/await based (asyncio)
  - Requires async threading model
  - Lower-level control
  - Better performance potential

- **Flask-SocketIO:**
  - Synchronous or eventlet/gevent
  - Integrates with Flask web framework
  - Higher-level abstractions
  - Easier Socket.IO client compatibility

**Required Decision:**
- [ ] Choose one library and document rationale
- [ ] Update all architecture diagrams
- [ ] Define threading model based on choice
- [ ] Update dependency specifications

**Recommendation Area:** See `DECISIONS.md` for evaluation criteria

---

### 2. Configuration Format Inconsistency (Affects All Phases)

**Status:** ⚠️ INCONSISTENT
**Impact:** Developer confusion, documentation mismatch
**Affected Phases:** All

**Inconsistencies Found:**
| Document | Specified Format | Location |
|----------|-----------------|----------|
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
```
monster-self-drive/
├── ImageProcessor.py
├── MonsterAuto.py
├── Settings.py
├── ThunderBorg.py
└── monsterWeb.py
```

**Proposed State (from CONSTITUTION):**
```
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

**Status:** ⚠️ SAFETY CRITICAL
**Impact:** Physical safety, robot control conflicts
**Affected Phases:** Phase 1

**Current Specification:**
- REQUIREMENTS mentions "3 simultaneous connections"
- **NOT SPECIFIED:** Who has control when multiple users connected

**Critical Questions:**
1. **Control Model:** Single-active-user or last-command-wins?
2. **Conflict Resolution:** What happens when two users send drive commands?
3. **Priority System:** Does admin override others?
4. **Handoff Mechanism:** How does control transfer between users?
5. **Safety Override:** Can any user trigger emergency stop?

**Safety Scenarios:**
- User A drives forward, User B drives backward simultaneously → ?
- User A in autonomous mode, User B switches to manual → ?
- User A has control, User B presses emergency stop → ?

**Required Decisions:**
- [ ] Define control arbitration model
- [ ] Specify command priority rules
- [ ] Document user role/permission system
- [ ] Define emergency stop behavior (all users? active user only?)
- [ ] Create state machine for multi-user interactions
- [ ] Add UI indicators showing who has control

**Safety Requirement:** MUST be resolved before Phase 1 completion

---

### 6. IMU Status Confusion (Phase 5 Blocker)

**Status:** ⚠️ CONFLICTING
**Impact:** Hardware requirements, budget, fallback behavior
**Affected Phases:** Phase 5

**Conflicting Specifications:**
| Document | IMU Status | Implication |
|----------|-----------|-------------|
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

**Status:** ⚠️ COMPLETELY MISSING
**Impact:** Hardware integration, pin conflicts
**Affected Phases:** Phase 1, 3, 5

**Missing Specifications:**

#### Ultrasonic Sensors
- [ ] Trigger pin(s): BCM pin numbers
- [ ] Echo pin(s): BCM pin numbers
- [ ] Number of sensors (1? 3? 5?)
- [ ] Power requirements (3.3V or 5V logic?)

#### Emergency Stop Button
- [ ] GPIO input pin: BCM pin number
- [ ] Pull-up/pull-down configuration
- [ ] Debounce strategy (hardware or software?)
- [ ] Active high or active low?

#### Status LEDs
- [ ] Power LED pin
- [ ] Status LED pin
- [ ] Error LED pin
- [ ] GPIO pin numbers
- [ ] Current-limiting resistor values

#### Wheel Encoders (if used)
- [ ] Left encoder pin(s)
- [ ] Right encoder pin(s)
- [ ] Interrupt-based or polling?
- [ ] Pulses per revolution

#### I2C Devices
- [ ] I2C bus number (i2c-1 typically)
- [ ] ThunderBorg address: Currently `0x15` (from code)
- [ ] IMU address: Not specified
- [ ] Other I2C devices and potential conflicts

**Required Actions:**
- [ ] Create complete GPIO pin assignment table
- [ ] Verify no pin conflicts
- [ ] Document pin configuration in setup guide
- [ ] Add pin validation to startup sequence

**Example Format Needed:**
```
| Component | Pin Type | BCM Pin | Config | Notes |
|-----------|----------|---------|--------|-------|
| Ultrasonic Trigger | GPIO Out | 23 | - | 5V tolerant |
| Ultrasonic Echo | GPIO In | 24 | Pull-down | Voltage divider required |
| Emergency Stop | GPIO In | 17 | Pull-up | Active low |
```

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
```
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

**Status:** ⚠️ HIGH-LEVEL ONLY
**Impact:** System stability, deadlocks, race conditions
**Affected Phases:** Phase 1, 2, 4

**Current State:** High-level mention of threading but missing critical details

#### Missing Specifications:

##### Thread Inventory and Priorities
- [ ] List all threads with purposes:
  - Web server thread(s)
  - WebSocket handler thread(s)
  - Video streaming thread
  - Image processing thread
  - Motor control thread
  - Sensor reading thread(s)
  - Safety monitor thread
- [ ] Priority assignments (if using real-time scheduling)
- [ ] CPU affinity settings (if multi-core)

##### Startup and Shutdown
- [ ] Thread startup sequence/order
- [ ] Dependency chains (which threads depend on others?)
- [ ] Graceful shutdown procedure
- [ ] Timeout values for thread joins
- [ ] Cleanup responsibilities per thread

##### Inter-Thread Communication
- [ ] Queue types (Queue, LifoQueue, PriorityQueue?)
- [ ] Queue sizes/bounds
- [ ] Message protocols/formats
- [ ] Synchronization primitives:
  - Locks: Which resources need locking?
  - Events: Thread coordination
  - Semaphores: Resource limiting
- [ ] Timeout strategies

##### Deadlock Prevention
- [ ] Lock acquisition ordering
- [ ] Timeout policies
- [ ] Deadlock detection mechanism?
- [ ] Recovery procedures

**Required Actions:**
- [ ] Create threading architecture diagram
- [ ] Document thread interaction patterns
- [ ] Define message passing protocols
- [ ] Specify error handling per thread
- [ ] Add thread monitoring/health checks

---

### 10. Safety System Integration

**Status:** ⚠️ REQUIREMENTS LISTED, INTEGRATION UNDEFINED
**Impact:** Physical safety, system reliability
**Affected Phases:** All (safety-critical)

**Current State:** Safety requirements listed but integration method unclear

#### Safety Checks Listed (from REQUIREMENTS):
- Battery voltage monitoring
- Motor overcurrent detection
- Obstacle detection
- Emergency stop
- Tilt detection (if IMU present)
- Communication timeout

#### Missing Integration Details:

##### Execution Location
Where do safety checks run?
- [ ] Decorator pattern on all motor commands?
- [ ] Middleware in web request pipeline?
- [ ] Dedicated safety monitor thread?
- [ ] Each module independently?

##### Priority and Order
- [ ] Which safety check runs first?
- [ ] Can checks be skipped in emergencies?
- [ ] Short-circuit evaluation order
- [ ] Performance budget per check

##### Emergency Stop Propagation
- [ ] How does emergency stop reach all subsystems?
- [ ] Stop signal mechanism (shared flag? event? queue message?)
- [ ] Guaranteed stop time requirement
- [ ] Motor brake vs. coast behavior

##### Recovery Procedures
- [ ] How to clear emergency state?
- [ ] Required checks before resuming operation
- [ ] User confirmation needed?
- [ ] System self-test after recovery

**Required Actions:**
- [ ] Design safety system architecture
- [ ] Create safety state machine
- [ ] Define safety check API
- [ ] Specify emergency stop propagation
- [ ] Document recovery procedures
- [ ] Add safety system to all architecture diagrams

---

### 11. Frame Rate Conflict

**Status:** ⚠️ CONFLICTING REQUIREMENTS
**Impact:** System performance expectations, hardware selection
**Affected Phases:** Phase 1, 2

**Conflicting Specifications:**
| Document | Requirement | Section | FPS Value |
|----------|------------|---------|-----------|
| REQUIREMENTS | "30 fps minimum" | TR2.1 | 30 fps |
| REQUIREMENTS | "30 fps minimum, 60 fps preferred" | PF1 | 30-60 fps |
| IMPLEMENTATION | "Skip frames if lagging" | 11.2 | ~15 fps effective |

**Analysis:**
- **Inconsistent minimums:** Some say 30 fps is minimum, others say preferred is 60
- **Frame skipping contradiction:** If 30 fps is minimum, frame skipping to 15 is non-compliant
- **Hardware implications:** 60 fps requires more powerful camera/CPU
- **Processing budget:** Higher FPS = less time per frame for processing

**Required Decisions:**
- [ ] Define absolute minimum FPS (hard requirement)
- [ ] Define target FPS (goal)
- [ ] Define acceptable FPS (degraded mode)
- [ ] Specify frame skip policy:
  - Skip frames to maintain processing quality?
  - OR reduce processing to maintain frame rate?
- [ ] Document FPS requirements per phase:
  - Phase 1 (basic streaming): ? fps
  - Phase 2 (with tracking): ? fps
  - Phase 4 (with autonomous): ? fps

**Hardware Considerations:**
- Raspberry Pi Camera V2: 30 fps @ 1080p, 60 fps @ 720p
- Processing capability limits real-world FPS

**Recommended Resolution:**
```
Minimum: 15 fps (degraded mode, warning shown)
Target: 30 fps (normal operation)
Preferred: 60 fps (if hardware allows, low processing load)
Policy: Maintain quality over frame rate (skip frames if needed)
```

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

#### Workflow Examples Needed:

**Distance Calibration Workflow:**
```
[UNDEFINED - Need to specify:
 - UI mockup
 - Step-by-step instructions
 - Visual feedback
 - Error handling
 - Success confirmation]
```

**Odometry Calibration Workflow:**
```
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
|-------|--------------|--------------|----------------|-------------------|
| **Config Format** | JSON or INI | Not specified | Settings.py (Python) | ✅ Choose ONE format |
| **Directory Structure** | Not mentioned | `src/` structure | Not mentioned | ✅ Decide migrate or stay flat |
| **Type Hints** | Recommended | Required | Not mentioned | ✅ Clarify requirement level |
| **IMU Status** | Optional ("Recommended") | Integrated module | Required ("Source and install") | ✅ Clarify required vs optional |
| **Tracking Algorithms** | 4 listed (KCF, CSRT, MOSSE, Template) | Not specified | 5 listed (+ Color-based) | ✅ Define MVP + roadmap |
| **WebSocket Library** | Both mentioned | Not specified | Not specified | ✅ Choose one library |
| **Frame Rate** | 30 fps min | Not specified | Skip frames (~15 fps) | ✅ Define min/target/preferred |
| **Multi-User** | "3 connections" supported | Not specified | Not specified | ✅ Define control model |
| **Safety Integration** | Checks listed | Not specified | Not specified | ✅ Define architecture |

---

## 📊 Priority Matrix

### P0 - Blockers (Must Resolve Immediately)
1. **WebSocket Library Choice** - Cannot start Phase 1 without this
2. **Multi-User Behavior** - Safety critical
3. **GPIO Pin Assignments** - Required for hardware setup
4. **Safety System Integration** - Safety critical

### P1 - High Priority (Resolve Before Implementation)
5. **Configuration Format** - Affects all development
6. **Directory Structure** - Affects imports and organization
7. **Threading Model Details** - Affects stability
8. **Frame Rate Specification** - Affects hardware selection

### P2 - Medium Priority (Resolve During Phase 1-2)
9. **Tracking Algorithm Priority** - Needed before Phase 2
10. **Calibration Procedures** - Needed before Phase 1 complete
11. **Hardware Setup Guide** - Needed for initial setup

### P3 - Lower Priority (Resolve Before Later Phases)
12. **IMU Status** - Phase 5 concern
13. **Deployment & Installation** - Production concern
14. **Calibration UI/Workflows** - UX improvement

---

## ✅ Resolution Process

### For Each Gap:

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

### Immediate Actions Required:

1. **Create `DECISIONS.md`** to track architectural decisions
2. **Prioritize P0 gaps** for immediate resolution
3. **Assign owners** to each gap (if team project)
4. **Set deadlines** for gap resolution
5. **Review existing code** to understand current state
6. **Update project timeline** based on resolution time

### Documentation Improvements:

- [ ] Create master glossary for consistent terminology
- [ ] Add cross-references between documents
- [ ] Create decision log for all choices
- [ ] Maintain change history for requirements

---

## 🔗 Related Documents

- `DECISIONS.md` - Architectural decisions and rationale
- `REQUIREMENTS.md` - System requirements (needs updates)
- `CONSTITUTION.md` - Code standards (needs updates)
- `IMPLEMENTATION.md` - Implementation plan (needs updates)
- `docs/architecture/` - Detailed architecture diagrams (to be created)

---

**Document Status:** Living document - update as gaps are resolved
**Review Frequency:** Before each phase kickoff
**Owner:** Project Lead
**Last Review:** 2025-12-06
