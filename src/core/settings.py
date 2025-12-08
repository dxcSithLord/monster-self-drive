#!/usr/bin/env python
# coding: utf-8
"""Settings loader for MonsterBorg self-driving code.

This module loads configuration from config/config.json and provides
basic validation (required sections check). It provides the same interface
as the legacy Settings.py for backward compatibility.

Note:
    Full JSON Schema validation is not implemented. The module validates
    that required config sections exist but does not validate against
    config/config.schema.json. The schema file is provided for documentation
    and can be used by external tools or a future implementation.

See Also:
    - config/config.json: Configuration file
    - config/config.schema.json: JSON Schema for documentation/external validation
    - docs/DECISIONS.md: ADR-002 for configuration format decision
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Tuple

# Module logger
_logger = logging.getLogger(__name__)

# Determine config path relative to this file
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_SCHEMA_FILE = _CONFIG_DIR / "config.schema.json"


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and validate configuration from JSON file.

    Args:
        config_path: Optional path to config file. Defaults to config/config.json.

    Returns:
        Dict containing configuration values.

    Raises:
        ConfigurationError: If config file is missing or invalid.
        FileNotFoundError: If config file does not exist.
        json.JSONDecodeError: If config file is not valid JSON.
    """
    if config_path is None:
        config_path = _CONFIG_FILE

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Basic validation - check required sections exist
    required_sections = [
        "security",
        "power",
        "camera",
        "processing",
        "control",
        "drive",
        "debug",
        "safety",
    ]
    for section in required_sections:
        if section not in config:
            raise ConfigurationError(f"Missing required config section: {section}")

    return config


class Settings:
    """Configuration settings container with backward-compatible interface.

    This class loads settings from config.json and exposes them as attributes
    for compatibility with existing code that imports Settings.

    Attributes:
        All configuration values are exposed as class attributes matching
        the legacy Settings.py interface.
    """

    _config: ClassVar[Dict[str, Any]] = {}
    _loaded: ClassVar[bool] = False

    # =========================================================================
    # Security settings
    # =========================================================================
    webBindAddress: str = "127.0.0.1"
    webPort: int = 8080

    # =========================================================================
    # Power settings
    # =========================================================================
    voltageIn: float = 12.0
    voltageOut: float = 11.4

    # =========================================================================
    # Camera settings
    # =========================================================================
    cameraWidth: int = 640
    cameraHeight: int = 480
    frameRate: int = 30
    flippedImage: bool = True
    jpegQuality: int = 80
    displayRate: int = 10

    # =========================================================================
    # Processing settings
    # =========================================================================
    scaledWidth: int = 160
    scaledHeight: int = 120
    processingThreads: int = 4
    minHuntColour: Tuple[int, int, int] = (80, 0, 0)
    maxHuntColour: Tuple[int, int, int] = (255, 100, 100)
    erodeSize: int = 5
    targetY1: int = 108  # int(scaledHeight * 0.9)
    targetY2: int = 72  # int(scaledHeight * 0.6)

    # =========================================================================
    # Control settings (PID)
    # =========================================================================
    motorSmoothing: int = 5
    positionP: float = 1.00
    positionI: float = 0.00
    positionD: float = 0.40
    changeP: float = 1.00
    changeI: float = 0.00
    changeD: float = 0.40
    clipI: int = 100

    # =========================================================================
    # Final drive settings
    # =========================================================================
    steeringGain: float = 1.0
    steeringClip: float = 1.0
    steeringOffset: float = 0.0

    # =========================================================================
    # Debug display settings
    # =========================================================================
    fpsInterval: int = 30  # frameRate
    showFps: bool = True
    testMode: bool = True
    showImages: bool = True
    overlayOriginal: bool = True
    showPerSecond: int = 1
    scaleFinalImage: float = 1.0
    targetLine: Tuple[int, int, int] = (0, 255, 255)
    targetPoints: Tuple[int, int, int] = (255, 255, 0)
    targetPointSize: int = 3

    # =========================================================================
    # Safety settings (ADR-009)
    # =========================================================================
    batteryStopVoltage: float = 10.5
    batteryWarningVoltage: float = 11.0
    watchdogTimeoutSeconds: float = 1.0
    emergencyStopEnabled: bool = True

    # =========================================================================
    # Path settings
    # =========================================================================
    photoDirectory: str = "~/monster-photos"

    # =========================================================================
    # Shared runtime values (not from config)
    # =========================================================================
    running: bool = True
    currentSpeed: float = 1.0
    testModeCounter: int = 0
    MonsterMotors = None  # Function which runs the MonsterBorg motors
    displayFrame = None  # Image to show when running (if any)
    frameCounter: int = 0
    frameAnnounce: int = 0
    lastFrameStamp: float = 0
    frameLock = None  # threading.Lock
    processorPool = None  # List of available image processing threads
    capture = None  # OpenCV VideoCapture object
    controller = None  # Motor control thread

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> None:
        """Load configuration from JSON file and update class attributes.

        Args:
            config_path: Optional path to config file. Defaults to config/config.json.
        """
        if cls._loaded and config_path is None:
            return  # Already loaded default config

        config = load_config(config_path)
        cls._config = config
        cls._loaded = True

        # Map JSON config to class attributes
        # Security
        cls.webBindAddress = config["security"]["webBindAddress"]
        cls.webPort = config["security"].get("webPort", 8080)

        # Power
        cls.voltageIn = config["power"]["voltageIn"]
        cls.voltageOut = config["power"]["voltageOut"]

        # Camera
        cls.cameraWidth = config["camera"]["width"]
        cls.cameraHeight = config["camera"]["height"]
        cls.frameRate = config["camera"]["frameRate"]
        cls.flippedImage = config["camera"]["flippedImage"]
        cls.jpegQuality = config["camera"].get("jpegQuality", 80)
        cls.displayRate = config["camera"].get("displayRate", 10)

        # Processing
        cls.scaledWidth = config["processing"]["scaledWidth"]
        cls.scaledHeight = config["processing"]["scaledHeight"]
        cls.processingThreads = config["processing"]["processingThreads"]
        cls.minHuntColour = tuple(config["processing"]["minHuntColour"])
        cls.maxHuntColour = tuple(config["processing"]["maxHuntColour"])
        cls.erodeSize = config["processing"]["erodeSize"]

        # Calculate target Y positions from ratios
        y1_ratio = config["processing"].get("targetY1Ratio", 0.9)
        y2_ratio = config["processing"].get("targetY2Ratio", 0.6)
        cls.targetY1 = int(cls.scaledHeight * y1_ratio)
        cls.targetY2 = int(cls.scaledHeight * y2_ratio)

        # Control (PID)
        cls.motorSmoothing = config["control"]["motorSmoothing"]
        cls.positionP = config["control"]["positionP"]
        cls.positionI = config["control"]["positionI"]
        cls.positionD = config["control"]["positionD"]
        cls.changeP = config["control"]["changeP"]
        cls.changeI = config["control"]["changeI"]
        cls.changeD = config["control"]["changeD"]
        cls.clipI = config["control"]["clipI"]

        # Drive
        cls.steeringGain = config["drive"]["steeringGain"]
        cls.steeringClip = config["drive"]["steeringClip"]
        cls.steeringOffset = config["drive"]["steeringOffset"]

        # Debug
        cls.showFps = config["debug"]["showFps"]
        cls.testMode = config["debug"]["testMode"]
        cls.showImages = config["debug"]["showImages"]
        cls.overlayOriginal = config["debug"].get("overlayOriginal", True)
        cls.showPerSecond = config["debug"].get("showPerSecond", 1)
        cls.scaleFinalImage = config["debug"].get("scaleFinalImage", 1.0)
        cls.targetLine = tuple(config["debug"].get("targetLineColour", [0, 255, 255]))
        cls.targetPoints = tuple(
            config["debug"].get("targetPointsColour", [255, 255, 0])
        )
        cls.targetPointSize = config["debug"].get("targetPointSize", 3)
        cls.fpsInterval = cls.frameRate

        # Safety (ADR-009)
        cls.batteryStopVoltage = config["safety"]["batteryStopVoltage"]
        cls.batteryWarningVoltage = config["safety"]["batteryWarningVoltage"]
        cls.watchdogTimeoutSeconds = config["safety"]["watchdogTimeoutSeconds"]
        cls.emergencyStopEnabled = config["safety"]["emergencyStopEnabled"]

        # Paths
        cls.photoDirectory = os.path.expanduser(
            config.get("paths", {}).get("photoDirectory", "~/monster-photos")
        )

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Return the raw configuration dictionary.

        Returns:
            Dict containing all configuration values.
        """
        if not cls._loaded:
            cls.load()
        return cls._config

    @classmethod
    def reload(cls) -> None:
        """Force reload configuration from file."""
        cls._loaded = False
        cls.load()


# Auto-load configuration on module import for backward compatibility
try:
    Settings.load()
except FileNotFoundError:
    # Config file not found - use defaults
    # This allows the module to be imported even if config doesn't exist yet
    pass
except json.JSONDecodeError as e:
    _logger.warning("Invalid JSON in config file: %s", e)
except ConfigurationError as e:
    _logger.warning("Configuration validation error: %s", e)
except PermissionError as e:
    _logger.warning("Permission denied reading config file: %s", e)
except OSError as e:
    _logger.warning("OS error reading config file: %s", e)


# =========================================================================
# Backward compatibility - dynamic attribute proxy (Python 3.7+ required)
# =========================================================================
# This allows: `from src.core.settings import frameRate`
# to work the same as: `Settings.frameRate`
# and properly reflects values after Settings.reload()

# List of all forwarded attribute names for __dir__
_FORWARDED_ATTRS = [
    # Security settings
    "webBindAddress",
    "webPort",
    # Power settings
    "voltageIn",
    "voltageOut",
    # Camera settings
    "cameraWidth",
    "cameraHeight",
    "frameRate",
    "flippedImage",
    "jpegQuality",
    "displayRate",
    # Processing settings
    "scaledWidth",
    "scaledHeight",
    "processingThreads",
    "minHuntColour",
    "maxHuntColour",
    "erodeSize",
    "targetY1",
    "targetY2",
    # Control settings (PID)
    "motorSmoothing",
    "positionP",
    "positionI",
    "positionD",
    "changeP",
    "changeI",
    "changeD",
    "clipI",
    # Drive settings
    "steeringGain",
    "steeringClip",
    "steeringOffset",
    # Debug settings
    "fpsInterval",
    "showFps",
    "testMode",
    "showImages",
    "overlayOriginal",
    "showPerSecond",
    "scaleFinalImage",
    "targetLine",
    "targetPoints",
    "targetPointSize",
    # Safety settings (ADR-009)
    "batteryStopVoltage",
    "batteryWarningVoltage",
    "watchdogTimeoutSeconds",
    "emergencyStopEnabled",
    # Path settings
    "photoDirectory",
    # Shared runtime values (not from config)
    "running",
    "currentSpeed",
    "testModeCounter",
    "MonsterMotors",
    "displayFrame",
    "frameCounter",
    "frameAnnounce",
    "lastFrameStamp",
    "frameLock",
    "processorPool",
    "capture",
    "controller",
]


def __getattr__(name: str):
    """Dynamic attribute forwarding to Settings class.

    This enables module-level attribute access that reflects the current
    Settings values, even after Settings.reload() is called.

    Note: Requires Python 3.7+ for module-level __getattr__ support.

    Args:
        name: Attribute name to look up

    Returns:
        The current value from Settings class

    Raises:
        AttributeError: If the attribute doesn't exist on Settings
    """
    if name in _FORWARDED_ATTRS:
        return getattr(Settings, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """List available module attributes including forwarded Settings attributes.

    Returns:
        List of all module attribute names
    """
    # Get the standard module attributes
    module_attrs = list(globals().keys())
    # Add forwarded attributes
    return module_attrs + _FORWARDED_ATTRS
