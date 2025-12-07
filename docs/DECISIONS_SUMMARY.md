# Architectural Decisions Summary

**Date:** 2025-12-07
**Session:** All ADRs Complete
**Status:** 10 of 10 ADRs ACCEPTED ✅

---

## ✅ Decisions Accepted

### ADR-001: WebSocket Library Selection (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** Flask-SocketIO
**Why:** Integrates with existing Flask, adequate performance for single-user control, automatic reconnection

### ADR-002: Configuration Format (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** JSON with Python Wrapper
**Why:** Industry standard, web UI integration, Settings.py validates JSON
**Action:** Convert Settings.py key-value pairs to config.json

### ADR-003: Directory Structure (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** Structured Source/Release Separation
**Why:** Scalability, professional structure, clear separation of concerns
**Action:** Migrate to src/ structure before Phase 1

### ADR-004: Multi-User Control Model (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** Single Active User Model
**Why:** Safety first, prevents conflicting commands
**Details:**

- One user has control, others are observers
- Second user can request takeover or auto-gains when first disconnects
- ANY user can trigger emergency stop

### ADR-005: Tracking Algorithm Strategy (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** Color-Based Tracking for MVP
**Why:** Lowest CPU load, 30+ fps on Pi 3B, sufficient for MVP
**Implementation:** HSV color space, configurable via web UI

### ADR-006: IMU Hardware Status (2025-12-06)

**Status:** 🟢 ACCEPTED
**Decision:** IMU Optional - Image-Based Inversion Detection
**Why:** No additional hardware needed for MVP
**Inversion Detection:**

1. Analyze camera image for orientation
2. If indeterminate: Rotate 360° and re-assess (max 3 attempts)
3. If still indeterminate: STOP and flash SOS LED pattern

**SOS Pattern:** `... --- ...` (Morse code SOS)

- Short flash: 0.2 seconds
- Long flash: 0.6 seconds
- Repeat until user intervention

### ADR-007: Frame Rate Requirements (2025-12-07)

**Status:** 🟢 ACCEPTED
**Decision:** Adaptive Frame Rate with Speed Limiting
**Why:** Safety-first approach linking frame rate to robot speed
**Implementation:**

- 15 fps minimum → 50% max speed
- 30 fps target → 100% max speed
- >30 fps → no additional benefit
- Quality over quantity (skip frames under load)

### ADR-008: Threading Model (2025-12-07)

**Status:** 🟢 ACCEPTED
**Decision:** Priority-Based Threading with Safety-First
**Why:** Ensures safety operations have highest priority
**Architecture:**

- Tier 1 (Highest): Motor Control + Safety Monitor (equal priority)
- Tier 2 (Medium): Video Streaming + Image Processing
- Tier 3 (Lowest): Web Server
- Web stop button links directly to Safety Monitor

### ADR-009: Safety System Architecture (2025-12-07)

**Status:** 🟢 ACCEPTED
**Decision:** Multi-Layer Safety with Mode-Dependent Behavior
**Why:** Defense in depth, appropriate for manual vs autonomous modes
**Layers:**

1. Hardware (ThunderBorg): 250ms failsafe
2. Watchdog Thread: 1 second timeout
3. Safety Monitor Thread: 10Hz polling, mode-dependent checks

**Mode-Dependent:**

- Manual: Driver responsibility, stop on signal loss only
- Autonomous: Mandatory battery/fault checks, stop on issues

### ADR-010: GPIO Pin Assignments (2025-12-07)

**Status:** 🟢 ACCEPTED
**Decision:** Document ThunderBorg HAT Usage, No Additional GPIO Needed
**Why:** MonsterBorg fully built, ThunderBorg provides all needed features
**Current Usage:**

- I2C pins 2/3 (ThunderBorg at address 0x15)
- ThunderBorg onboard: 2x motors, 2x RGB LEDs, battery monitor, fault
  detection
- No additional GPIO required for Phase 1

---

## 📊 Progress Summary

**P0 Blockers Resolved:** 4 of 4 (100%) ✅

- ✅ WebSocket Library (ADR-001)
- ✅ Multi-User Control (ADR-004)
- ✅ GPIO Pin Assignments (ADR-010)
- ✅ Safety System Integration (ADR-009)

**P1 High Priority Resolved:** 5 of 5 (100%) ✅

- ✅ Configuration Format (ADR-002)
- ✅ Directory Structure (ADR-003)
- ✅ Tracking Algorithm (ADR-005)
- ✅ Frame Rate Requirements (ADR-007)
- ✅ Threading Model (ADR-008)

**P3 Lower Priority Resolved:** 1 of 1 (100%) ✅

- ✅ IMU Status (ADR-006)

**Overall ADR Progress:** 10 of 10 accepted (100%) ✅

**All architectural decisions complete - Ready for implementation!**

---

## 🎯 Ready for Phase 1

### ✅ All Prerequisites Complete

1. ✅ Flask-SocketIO web server implementation
2. ✅ Single-user control manager implementation
3. ✅ JSON configuration system
4. ✅ Directory structure migration
5. ✅ Color-based tracking implementation
6. ✅ Image-based inversion detection
7. ✅ GPIO pin assignments documented
8. ✅ Safety system architecture designed
9. ✅ Threading model defined
10. ✅ Frame rate requirements clarified

**All P0 and P1 ADRs resolved - Phase 1 implementation can begin!**

---

## 📋 Implementation Checklist

### Architectural Planning (COMPLETE)

- [x] All 10 ADRs documented and accepted
- [x] GPIO pin assignments defined (ADR-010)
- [x] Safety system architecture designed (ADR-009)
- [x] Threading model defined (ADR-008)
- [x] Frame rate requirements clarified (ADR-007)

### Pre-Phase 1 Migrations (TO DO)

- [ ] Migrate to src/ directory structure
- [ ] Convert Settings.py to JSON loader
- [ ] Create config.json with all current settings
- [ ] Create JSON Schema for validation

### Phase 1 Implementation (TO DO)

- [ ] Implement Flask-SocketIO server
- [ ] Create Motor Control Thread (Tier 1)
- [ ] Create Safety Monitor Thread (Tier 1)
- [ ] Implement ControlManager for single-user control
- [ ] Create web UI configuration view page
- [ ] Add control status indicators to web UI
- [ ] Implement emergency stop (accessible to any user)
- [ ] Implement FPS-based speed limiting

### Phase 2 Implementation (TO DO)

- [ ] Implement HSV color-based tracking
- [ ] Add color range configuration to web UI
- [ ] Implement image-based inversion detection
- [ ] Implement 360° rotation procedure
- [ ] Implement SOS LED flash pattern
- [ ] Performance test on Raspberry Pi 3B

---

## 🔧 Technical Specifications

### Directory Structure (Post-Migration)

```text
monster-self-drive/
├── src/
│   ├── core/ (settings, monster_auto)
│   ├── web/ (Flask-SocketIO server)
│   ├── vision/ (tracking, image_processor)
│   ├── hardware/ (thunderborg, motors)
│   └── safety/ (control_manager, emergency_stop)
├── config/
│   ├── config.json
│   └── config.schema.json
├── docs/
├── tests/
├── release/  (git-ignored)
├── static/
├── templates/
└── requirements.txt
```

### Dependencies Update

- Flask >= 3.0.0
- Flask-SocketIO >= 5.3.0
- python-socketio >= 5.10.0

### Performance Targets

- Frame rate: 30 fps (target), 15 fps (acceptable minimum)
- WebSocket latency: 20-30ms (acceptable for single-user)
- Processing budget: <33ms per frame

### Safety Specifications

- **Multi-Layer Safety:**
  - Layer 1: ThunderBorg hardware failsafe (250ms)
  - Layer 2: Watchdog thread (1 second timeout)
  - Layer 3: Safety Monitor thread (10Hz polling)
- **Mode-Dependent:** Manual (driver responsibility) vs Autonomous
  (mandatory checks)
- **Emergency Stop:** Accessible to ANY user, <100ms response time
- **Battery Thresholds:** 10.5V stop (auto), 11.0V warning (manual)
- **Speed Limiting:** FPS-based (15fps→50%, 30fps→100%)

### Threading Architecture

- **Tier 1 (Equal Highest):** Motor Control + Safety Monitor
- **Tier 2 (Medium):** Video Streaming + Image Processing
- **Tier 3 (Lowest):** Web Server
- **Communication:** Queue-based with timeouts, lock-free emergency stop
- **Deadlock Prevention:** Lock ordering, 100ms timeouts, no nested locks

---

## 📝 Next Steps

1. **✅ All architectural decisions complete**

2. **Execute pre-Phase 1 migrations:**
   - Migrate to src/ directory structure
   - Convert Settings.py to JSON loader
   - Create config.json with current settings
   - Create JSON Schema for validation

3. **Begin Phase 1 implementation:**
   - Flask-SocketIO server with threading model
   - Motor Control and Safety Monitor threads (Tier 1)
   - Single-user ControlManager
   - Web UI with control status indicators
   - Emergency stop button (any user access)
   - FPS-based speed limiting

---

**Document Status:** All ADRs complete as of 2025-12-07
**See Also:** docs/DECISIONS.md for complete ADR details (all 10 accepted)
**See Also:** docs/CRITICAL_GAPS.md for gap resolution status
