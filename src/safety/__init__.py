"""Safety module for control management and emergency stop.

This module implements the multi-layer safety architecture from ADR-009:

Layer 1 (Hardware): ThunderBorg 250ms failsafe
    - Built into ThunderBorg hardware
    - Automatically stops motors if no commands received

Layer 2 (Watchdog): 1 second timeout
    - Software watchdog thread
    - Stops motors on communication loss

Layer 3 (Safety Monitor): 10Hz polling
    - Mode-dependent safety checks
    - Battery monitoring
    - Fault detection

Threading Priority (ADR-008):
    - Tier 1 (Highest): Motor Control + Safety Monitor (equal priority)
    - Tier 2 (Medium): Video Streaming + Image Processing
    - Tier 3 (Lowest): Web Server

Emergency Stop:
    - Accessible to ANY user
    - Target response time: <100ms
    - Lock-free implementation

See Also:
    - docs/DECISIONS.md: ADR-009 for safety system architecture
    - docs/DECISIONS.md: ADR-008 for threading model
    - config/config.json: safety section for thresholds
"""

from .control_manager import ControlManager
from .emergency_stop import EmergencyStop
from .safety_monitor import SafetyMonitor

__all__ = ["ControlManager", "EmergencyStop", "SafetyMonitor"]
