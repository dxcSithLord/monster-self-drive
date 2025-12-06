# Architectural Decisions Summary

**Date:** 2025-12-06
**Session:** Critical Gaps Resolution
**Status:** 6 of 10 ADRs ACCEPTED

---

## ✅ Decisions Accepted Today

### ADR-001: WebSocket Library Selection
**Status:** 🟢 ACCEPTED
**Decision:** Flask-SocketIO
**Why:** Integrates with existing Flask, adequate performance for single-user control, automatic reconnection

### ADR-002: Configuration Format
**Status:** 🟢 ACCEPTED
**Decision:** JSON with Python Wrapper
**Why:** Industry standard, web UI integration, Settings.py validates JSON
**Action:** Convert Settings.py key-value pairs to config.json

### ADR-003: Directory Structure
**Status:** 🟢 ACCEPTED
**Decision:** Structured Source/Release Separation
**Why:** Scalability, professional structure, clear separation of concerns
**Action:** Migrate to src/ structure before Phase 1

### ADR-004: Multi-User Control Model
**Status:** 🟢 ACCEPTED
**Decision:** Single Active User Model
**Why:** Safety first, prevents conflicting commands
**Details:**
- One user has control, others are observers
- Second user can request takeover or auto-gains when first disconnects
- ANY user can trigger emergency stop

### ADR-005: Tracking Algorithm Strategy
**Status:** 🟢 ACCEPTED
**Decision:** Color-Based Tracking for MVP
**Why:** Lowest CPU load, 30+ fps on Pi 3B, sufficient for MVP
**Implementation:** HSV color space, configurable via web UI

### ADR-006: IMU Hardware Status
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

---

## 🟡 Remaining Decisions

### ADR-007: Frame Rate Requirements
**Status:** 🟡 PROPOSED
**Note:** Partially addressed in ADR-005 (30 fps target for color tracking)

### ADR-008: Threading Model
**Status:** 🟡 PROPOSED
**Note:** Will be influenced by Flask-SocketIO threading mode selection

### ADR-009: Safety System Architecture
**Status:** 🟡 PROPOSED
**Priority:** P0 - Must resolve
**Dependencies:** Needs GPIO pin assignments (ADR-010)

### ADR-010: GPIO Pin Assignments
**Status:** 🟡 PROPOSED
**Priority:** P0 - Must resolve
**Needed for:** Ultrasonic sensors, emergency stop button, status LEDs, wheel encoders

---

## 📊 Progress Summary

**P0 Blockers Resolved:** 2 of 4 (50%)
- ✅ WebSocket Library (ADR-001)
- ✅ Multi-User Control (ADR-004)
- ⏳ GPIO Pin Assignments (ADR-010)
- ⏳ Safety System Integration (ADR-009)

**P1 High Priority Resolved:** 3 of 4 (75%)
- ✅ Configuration Format (ADR-002)
- ✅ Directory Structure (ADR-003)
- ✅ Tracking Algorithm (ADR-005)
- ⏳ Frame Rate (ADR-007) - Partially addressed

**P3 Lower Priority Resolved:** 1 of 1 (100%)
- ✅ IMU Status (ADR-006)

**Overall ADR Progress:** 6 of 10 accepted (60%)

---

## 🎯 Ready for Phase 1

### Can Proceed With:
1. ✅ Flask-SocketIO web server implementation
2. ✅ Single-user control manager implementation
3. ✅ JSON configuration system
4. ✅ Directory structure migration
5. ✅ Color-based tracking implementation
6. ✅ Image-based inversion detection

### Still Needed Before Full Phase 1:
1. ⏳ GPIO pin assignments (hardware integration)
2. ⏳ Safety system architecture design
3. ⏳ Threading model details

---

## 📋 Implementation Checklist

### Immediate (Before Phase 1 Code)
- [ ] Migrate to src/ directory structure
- [ ] Convert Settings.py to JSON loader
- [ ] Create config.json with all current settings
- [ ] Create JSON Schema for validation
- [ ] Define GPIO pin assignments (ADR-010)
- [ ] Design safety system architecture (ADR-009)

### Phase 1 Implementation
- [ ] Implement Flask-SocketIO server
- [ ] Implement ControlManager for single-user control
- [ ] Create web UI configuration view page
- [ ] Add control status indicators to web UI
- [ ] Implement emergency stop (accessible to any user)

### Phase 2 Implementation
- [ ] Implement HSV color-based tracking
- [ ] Add color range configuration to web UI
- [ ] Implement image-based inversion detection
- [ ] Implement 360° rotation procedure
- [ ] Implement SOS LED flash pattern
- [ ] Performance test on Raspberry Pi 3B

---

## 🔧 Technical Specifications

### Directory Structure (Post-Migration)
```
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
- Single active user control
- Emergency stop accessible to ANY user
- SOS LED pattern for critical failures
- Image-based inversion detection with 3-attempt retry
- Motor rotation and visual odometry for navigation

---

## 📝 Next Steps

1. **Complete remaining P0 decisions:**
   - Define GPIO pin assignments
   - Design safety system architecture

2. **Execute migrations:**
   - Directory structure
   - Configuration to JSON

3. **Begin Phase 1 implementation:**
   - Flask-SocketIO integration
   - Control manager
   - Web UI enhancements

---

**Document Status:** Summary of decisions made 2025-12-06
**See Also:** docs/DECISIONS.md for complete ADR details
**See Also:** docs/CRITICAL_GAPS.md for remaining gaps
