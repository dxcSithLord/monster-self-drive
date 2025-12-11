"""Web module for Flask-SocketIO server interface.

This module provides:
- Flask-SocketIO web server (ADR-001)
- Single-user control manager (ADR-004)
- Control status indicators
- Emergency stop button (accessible to any user)
- Mobile-optimized responsive interface

Phase 1 Implementation:
- Responsive design for mobile devices
- Touch controls with continuous movement
- Virtual joystick
- WebSocket real-time communication
- Battery/connection status indicators

See Also:
    - docs/DECISIONS.md: ADR-001 for WebSocket library decision
    - docs/DECISIONS.md: ADR-004 for multi-user control model
    - docs/IMPLEMENTATION_PLAN.md: Phase 1 specification
"""

from src.web.server import MonsterWebServer

__all__ = ['MonsterWebServer']
