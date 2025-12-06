# ADR-010: GPIO Pin Assignments for MonsterBorg

**Status:** 🟡 PROPOSED (REQUIRES HARDWARE VALIDATION)
**Date:** 2025-12-06
**Deciders:** Project Lead + Hardware Validation Required
**Priority:** P0 - Critical for hardware integration

---

## ⚠️ VALIDATION REQUIRED

**This ADR contains PROPOSED pin assignments that MUST be validated against actual MonsterBorg hardware before implementation.**

**Hardware Documentation:** https://www.piborg.org/blog/build/monsterborg-build

**Please review the MonsterBorg build documentation and update this ADR with actual pin assignments.**

---

## Context

The MonsterBorg robot requires GPIO pin assignments for various sensors and indicators.

**Known Information from Codebase:**
- **ThunderBorg Motor Controller:** I2C address `0x15` (from ThunderBorg.py line 44)
- **I2C Bus:** Bus 1 (standard for Raspberry Pi 2/3/4)
- **I2C Hardware Pins:** GPIO 2 (SDA), GPIO 3 (SCL)
- **Camera:** CSI interface (not GPIO)

**Requirements from Documentation:**
- Ultrasonic distance sensors (Phase 3)
- Emergency stop button (Phase 1)
- Status LEDs for SOS pattern (Phase 2 - ADR-006)
- Optional: Wheel encoders (Phase 5)

---

## Proposed GPIO Pin Assignments

### I2C Devices (Hardware I2C Bus 1)

| Device | I2C Address | GPIO Pins | Status |
|--------|-------------|-----------|--------|
| **ThunderBorg Motor Controller** | 0x15 | GPIO 2 (SDA), GPIO 3 (SCL) | ✅ Confirmed from code |
| Future IMU (Optional) | 0x68 or 0x76 | Shared I2C bus | Phase 5+ |

**Notes:**
- Hardware I2C provides DMA support and higher reliability
- Multiple I2C devices share the same bus
- Ensure no I2C address conflicts

---

### ThunderBorg Interface Library (ThunderBorg.py)

**Purpose:** Provides I2C-based interface to ThunderBorg motor controller board

**Key Features from ThunderBorg.py:**

#### Motor Control Functions
- `SetMotor1(power)` - Set motor 1 power (-1.0 to +1.0)
- `SetMotor2(power)` - Set motor 2 power (-1.0 to +1.0)
- `SetMotors(power)` - Set both motors to same power
- `SetMotor1(0)` / `SetMotor2(0)` - Stop motors
- `GetMotor1()` / `GetMotor2()` - Read current motor power settings

#### Onboard LED Control (ThunderBorg Board LEDs)
The ThunderBorg board includes two onboard RGB LEDs controllable via I2C:

- `SetLed1(r, g, b)` - Set ThunderBorg LED (RGB 0.0-1.0)
- `SetLed2(r, g, b)` - Set ThunderBorg Lid LED (RGB 0.0-1.0)
- `SetLeds(r, g, b)` - Set both LEDs to same color
- `GetLed1()` / `GetLed2()` - Read current LED colors
- `SetLedShowBattery(state)` - Enable/disable battery level display on LEDs
- `GetLedShowBattery()` - Check if battery display is enabled

**SOS Pattern Note:** The onboard ThunderBorg LEDs can be used for the SOS pattern (ADR-006) as an alternative to external GPIO LEDs, reducing GPIO pin requirements.

#### External LED Control (Optional SK9822/APA102C LEDs)
- `WriteExternalLedWord(b0, b1, b2, b3)` - Low-level serial LED control
- `SetExternalLedColours([[r,g,b], ...])` - Set RGB colors for external LED strips

These external LEDs are controlled via I2C commands (not direct GPIO), using the ThunderBorg board as an LED controller.

#### Battery Monitoring
- `GetBatteryReading()` - Read battery voltage
- `GetBatteryMonitoringLimits()` - Get min/max voltage thresholds
- `SetBatteryMonitoringLimits(min, max)` - Set voltage thresholds

#### Board Information
- `Init([busNumber])` - Initialize I2C communication (bus 1 default for Pi 2/3/4)
- `ScanForThunderBorg([busNumber])` - Scan I2C bus for ThunderBorg boards
- `SetNewAddress(newAddress)` - Change I2C address (persists after power cycle)
- `Help()` - Display all available functions

**I2C Communication Details:**
- Default I2C Address: `0x15` (configurable via `SetNewAddress`)
- I2C Bus: Bus 1 (GPIO 2 SDA, GPIO 3 SCL)
- Maximum I2C packet length: 6 bytes
- Supports multiple ThunderBorg boards with different addresses

**Implementation Example:**
```python
import ThunderBorg

# Initialize ThunderBorg
TB = ThunderBorg.ThunderBorg()
TB.Init()  # Uses I2C bus 1, address 0x15

# Motor control
TB.SetMotor1(0.5)   # 50% forward on motor 1
TB.SetMotor2(-0.3)  # 30% reverse on motor 2

# Use onboard LEDs for status
TB.SetLed1(0, 1, 0)  # Green = operational
TB.SetLed2(1, 0, 0)  # Red = error

# Emergency stop
TB.SetMotors(0)  # Stop all motors

# Battery check
voltage = TB.GetBatteryReading()
if voltage < 10.5:  # Low battery warning
    TB.SetLeds(1, 1, 0)  # Yellow LEDs
```

---

### Emergency Stop Button (MVP - Required)

| Component | GPIO Pin | Configuration | Priority |
|-----------|----------|---------------|----------|
| Emergency Stop Button | **GPIO 17** | Input, Pull-up, Active LOW | **P0 - MVP** |

**Configuration Details:**
- Internal pull-up resistor enabled (`GPIO.PUD_UP`)
- Active LOW: Button pressed = GPIO reads 0
- Software debounce: 20ms
- Highest priority interrupt

**Implementation:**
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Interrupt callback
def emergency_stop_callback(channel):
    stop_all_motors()
    broadcast_emergency_stop()

GPIO.add_event_detect(17, GPIO.FALLING, callback=emergency_stop_callback, bouncetime=20)
```

---

### Status LEDs (MVP - Required for SOS Pattern)

| LED | GPIO Pin | Color | Configuration | Purpose |
|-----|----------|-------|---------------|---------|
| Power/Status LED | **GPIO 27** | Green | Output, Active HIGH | System operational |
| Activity LED | **GPIO 22** | Blue | Output, Active HIGH | Processing activity |
| Error/SOS LED | **GPIO 10** | Red | Output, Active HIGH | SOS Morse code (ADR-006) |

**LED Specifications:**
- Forward voltage: ~2V (typical LED)
- Current: 20mA maximum
- Current-limiting resistor: **220Ω** (standard)
  - Calculation: (3.3V - 2V) / 0.02A = 65Ω minimum, 220Ω typical
- Active HIGH: GPIO = 1 → LED ON

**SOS Pattern Implementation (from ADR-006):**
```python
# SOS Pattern: ... --- ... (3 short, 3 long, 3 short)
SHORT_FLASH = 0.2  # seconds
LONG_FLASH = 0.6   # seconds
FLASH_GAP = 0.2
PATTERN_GAP = 2.0

def flash_sos():
    while True:
        for _ in range(3):  # S
            GPIO.output(10, GPIO.HIGH)
            time.sleep(SHORT_FLASH)
            GPIO.output(10, GPIO.LOW)
            time.sleep(FLASH_GAP)

        for _ in range(3):  # O
            GPIO.output(10, GPIO.HIGH)
            time.sleep(LONG_FLASH)
            GPIO.output(10, GPIO.LOW)
            time.sleep(FLASH_GAP)

        for _ in range(3):  # S
            GPIO.output(10, GPIO.HIGH)
            time.sleep(SHORT_FLASH)
            GPIO.output(10, GPIO.LOW)
            time.sleep(FLASH_GAP)

        time.sleep(PATTERN_GAP)
```

---

### Ultrasonic Distance Sensors (Phase 3)

| Sensor | Trigger Pin | Echo Pin | Configuration | Priority |
|--------|-------------|----------|---------------|----------|
| **Front Ultrasonic** | **GPIO 23** | **GPIO 24** | Trigger=Output, Echo=Input+Pull-down | Phase 3 |
| Left Ultrasonic (Optional) | GPIO 5 | GPIO 6 | Trigger=Output, Echo=Input+Pull-down | Future |
| Right Ultrasonic (Optional) | GPIO 13 | GPIO 19 | Trigger=Output, Echo=Input+Pull-down | Future |

**Ultrasonic Sensor Notes:**
- Typical sensor: HC-SR04 or compatible
- Trigger: Send 10μs pulse to initiate measurement
- Echo: Measures return pulse width (proportional to distance)
- **Voltage divider required if using 5V sensor:**
  - Echo pin output is 5V
  - Raspberry Pi GPIO max: 3.3V
  - Voltage divider: R1=1kΩ, R2=2kΩ (5V → 3.3V)
- Measurement timeout: 30ms (max range ~5 meters)

**Distance Calculation:**
```python
# Distance = (pulse_width_seconds * speed_of_sound) / 2
# Speed of sound: 343 m/s = 34300 cm/s
distance_cm = (pulse_width * 34300) / 2
```

---

### Wheel Encoders (Phase 5 - Optional)

| Encoder | GPIO Pin | Configuration | Priority |
|---------|----------|---------------|----------|
| Left Wheel Encoder | **GPIO 16** | Input, Pull-up, Interrupt | Phase 5 |
| Right Wheel Encoder | **GPIO 20** | Input, Pull-up, Interrupt | Phase 5 |

**Encoder Notes:**
- For improved odometry (complements visual odometry)
- Interrupt-driven for accuracy
- Software debounce required
- Quadrature encoders provide direction information

---

## Complete GPIO Pin Allocation Table

| BCM GPIO | Function | Direction | Pull | Voltage | Phase | Status |
|----------|----------|-----------|------|---------|-------|--------|
| **2** | I2C SDA (ThunderBorg) | I2C | - | 3.3V | MVP | ✅ Confirmed |
| **3** | I2C SCL (ThunderBorg) | I2C | - | 3.3V | MVP | ✅ Confirmed |
| 5 | Ultrasonic Left Trigger | Output | - | 3.3V | Future | Proposed |
| 6 | Ultrasonic Left Echo | Input | Pull-down | 3.3V | Future | Proposed |
| **10** | **Error/SOS LED (Red)** | Output | - | 3.3V | **MVP** | **Required** |
| 13 | Ultrasonic Right Trigger | Output | - | 3.3V | Future | Proposed |
| 16 | Left Wheel Encoder | Input | Pull-up | 3.3V | Phase 5 | Optional |
| **17** | **Emergency Stop Button** | Input | Pull-up | 3.3V | **MVP** | **Required** |
| 19 | Ultrasonic Right Echo | Input | Pull-down | 3.3V | Future | Proposed |
| 20 | Right Wheel Encoder | Input | Pull-up | 3.3V | Phase 5 | Optional |
| **22** | **Activity LED (Blue)** | Output | - | 3.3V | **MVP** | **Required** |
| **23** | **Ultrasonic Front Trigger** | Output | - | 3.3V | **Phase 3** | **Required** |
| **24** | **Ultrasonic Front Echo** | Input | Pull-down | 3.3V | **Phase 3** | **Required** |
| **27** | **Status LED (Green)** | Output | - | 3.3V | **MVP** | **Required** |

### Reserved/Do Not Use

| GPIO Pin | Reserved For | Reason |
|----------|--------------|--------|
| 0, 1 | I2C ID EEPROM | HAT identification |
| 4 | 1-Wire | Reserved for 1-Wire devices |
| 14, 15 | UART (Serial) | Console/debugging |
| 18, 21 | PCM Audio | Can be repurposed if not using audio |

---

## GPIO Usage Summary

**MVP (Phase 1-2):**
- I2C: 2 pins (GPIO 2, 3) - ThunderBorg motor control
- Emergency Stop: 1 pin (GPIO 17)
- Status LEDs: 3 pins (GPIO 10, 22, 27)
- **Total MVP: 6 GPIO pins**

**Phase 3 (Ultrasonic):**
- Front sensor: 2 pins (GPIO 23, 24)
- **Total with Phase 3: 8 GPIO pins**

**Phase 5 (Wheel Encoders):**
- Encoders: 2 pins (GPIO 16, 20)
- **Total with Phase 5: 10 GPIO pins**

**Optional Future:**
- Additional ultrasonics: 4 pins (GPIO 5, 6, 13, 19)
- **Maximum total: 14 GPIO pins**

**Remaining Available GPIO:** 14+ pins for future expansion

---

## Power and Current Budget

### GPIO Current Limits (Per Raspberry Pi Specifications)

- **Per GPIO pin:** 16mA maximum
- **Total all GPIO combined:** 50mA recommended maximum
- **3.3V rail total:** 500mA maximum (shared with all 3.3V components)

### Our Current Usage

**LEDs:**
- 3 LEDs × 20mA each = **60mA total**
- **⚠️ EXCEEDS recommended 50mA limit**

**Mitigation Options:**
1. **Reduce LED current to 15mA each** (total 45mA)
   - Use 330Ω resistors instead of 220Ω
   - Calculation: (3.3V - 2V) / 0.015A = 86.7Ω → use 330Ω standard value
   - Result: ~4.3mA per LED (safer, dimmer)

2. **Use external LED driver** (recommended for production)
   - Transistor driver (NPN transistor per LED)
   - LED driver IC (e.g., ULN2803)
   - Powers LEDs from 5V rail instead of GPIO

**Recommended:** Use 330Ω resistors for MVP, consider external driver for production.

---

## Safety Considerations

### Voltage Protection

1. **All GPIO inputs MUST be 3.3V maximum**
   - **DO NOT connect 5V directly to any GPIO pin**
   - Use voltage dividers for 5V sensors (ultrasonic echo pins)
   - Voltage divider example: R1=1kΩ (to 5V), R2=2kΩ (to GND) → 3.3V output

2. **No direct motor control via GPIO**
   - Motors controlled via ThunderBorg I2C only
   - ThunderBorg handles high current motor drive
   - GPIO pins cannot drive motors (insufficient current)

### Emergency Stop Priority

- Emergency stop button: **Highest priority**
- Interrupt-based detection (not polling)
- Immediate motor shutdown via ThunderBorg
- Debounce time: 20ms (balance between responsiveness and noise)

### Software Setup

```python
import RPi.GPIO as GPIO

def setup_gpio():
    """Initialize all GPIO pins for MonsterBorg"""
    GPIO.setmode(GPIO.BCM)

    # Emergency stop button (highest priority)
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(17, GPIO.FALLING,
                         callback=emergency_stop_handler,
                         bouncetime=20)

    # Status LEDs
    GPIO.setup(10, GPIO.OUT, initial=GPIO.LOW)   # Error LED
    GPIO.setup(22, GPIO.OUT, initial=GPIO.LOW)   # Activity LED
    GPIO.setup(27, GPIO.OUT, initial=GPIO.HIGH)  # Status LED (on at boot)

    # Ultrasonic sensor (Phase 3)
    GPIO.setup(23, GPIO.OUT, initial=GPIO.LOW)   # Trigger
    GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Echo

def cleanup_gpio():
    """Cleanup GPIO on shutdown"""
    # Turn off all LEDs
    GPIO.output(10, GPIO.LOW)
    GPIO.output(22, GPIO.LOW)
    GPIO.output(27, GPIO.LOW)

    # Reset GPIO
    GPIO.cleanup()
```

---

## Hardware Validation Checklist

**Before implementing these pin assignments, verify:**

- [ ] Check MonsterBorg build documentation at https://www.piborg.org/blog/build/monsterborg-build
- [ ] Verify ThunderBorg doesn't use any additional GPIO pins
- [ ] Confirm MonsterBorg board doesn't have pre-wired components on proposed pins
- [ ] Check if status LEDs already exist on ThunderBorg board (has 2 RGB LEDs)
- [ ] Verify ultrasonic sensor mounting locations and cable routing
- [ ] Confirm emergency stop button physical location
- [ ] Check power supply capacity for additional components
- [ ] Verify no pin conflicts with existing MonsterBorg hardware
- [ ] Test proposed pins with multimeter before connecting components
- [ ] Update this document with actual hardware configuration

---

## ThunderBorg Onboard Features

**Known from ThunderBorg.py:**
- 2 RGB LEDs onboard (controllable via I2C commands)
  - LED 1: ThunderBorg LED
  - LED 2: Lid LED
- Battery voltage monitoring (via I2C)
- Motor fault detection (via I2C)

**Question:** Can we use ThunderBorg's onboard LEDs instead of external GPIO LEDs?
- **Answer:** Partially - ThunderBorg has 2 RGB LEDs, we need 3 single-color LEDs for clear status
- **Recommendation:** Use ThunderBorg LEDs for status, add external red LED for SOS only

---

## Recommended Updates After Hardware Review

1. **Verify actual MonsterBorg pin usage** from build documentation
2. **Check if MonsterBorg has:**
   - Pre-installed ultrasonic sensors → use those pins
   - Pre-installed emergency stop → use that pin
   - Pre-installed LEDs → note which GPIO pins
3. **Update GPIO assignments** based on actual hardware
4. **Test each pin** before finalizing
5. **Document any additional MonsterBorg-specific hardware**
6. **Mark this ADR as ACCEPTED** after validation

---

## Action Items

- [ ] **CRITICAL:** Access https://www.piborg.org/blog/build/monsterborg-build and review GPIO usage
- [ ] Verify ThunderBorg I2C address (expected 0x15)
- [ ] Check MonsterBorg documentation for pre-wired components
- [ ] Test proposed GPIO pins with multimeter (ensure they're available)
- [ ] Decide: Use ThunderBorg onboard LEDs or external GPIO LEDs?
- [ ] Update pin assignments based on actual hardware
- [ ] Implement voltage dividers for 5V ultrasonic sensors
- [ ] Calculate and verify power budget
- [ ] Create wiring diagram with finalized pins
- [ ] Update requirements.txt if new libraries needed (e.g., RPi.GPIO)
- [ ] Mark ADR as ACCEPTED after hardware validation complete

---

## Status: PROPOSED - Awaiting Hardware Validation

**This ADR will remain PROPOSED until:**
1. Hardware documentation reviewed
2. Pin assignments verified against actual MonsterBorg board
3. Physical testing confirms no conflicts
4. All action items above completed

**After validation, update:**
- Status to 🟢 ACCEPTED
- Pin assignments with actual hardware configuration
- Add wiring diagrams
- Remove this notice

---

**Document Created:** 2025-12-06
**Requires Validation By:** Hardware team / Project lead with physical access to MonsterBorg
**Hardware Reference:** https://www.piborg.org/blog/build/monsterborg-build
