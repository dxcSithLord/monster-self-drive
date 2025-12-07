#!/usr/bin/env python
# coding: utf-8
"""Tests for settings loader."""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.settings import ConfigurationError, Settings, load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "security": {"webBindAddress": "127.0.0.1", "webPort": 8080},
            "power": {"voltageIn": 12.0, "voltageOut": 11.4},
            "camera": {
                "width": 640,
                "height": 480,
                "frameRate": 30,
                "flippedImage": True,
            },
            "processing": {
                "scaledWidth": 160,
                "scaledHeight": 120,
                "processingThreads": 4,
                "minHuntColour": [80, 0, 0],
                "maxHuntColour": [255, 100, 100],
                "erodeSize": 5,
            },
            "control": {
                "motorSmoothing": 5,
                "positionP": 1.0,
                "positionI": 0.0,
                "positionD": 0.4,
                "changeP": 1.0,
                "changeI": 0.0,
                "changeD": 0.4,
                "clipI": 100,
            },
            "drive": {
                "steeringGain": 1.0,
                "steeringClip": 1.0,
                "steeringOffset": 0.0,
            },
            "debug": {"showFps": True, "testMode": True, "showImages": True},
            "safety": {
                "batteryStopVoltage": 10.5,
                "batteryWarningVoltage": 11.0,
                "watchdogTimeoutSeconds": 1.0,
                "emergencyStopEnabled": True,
            },
        }
        config_file.write_text(json.dumps(config_data))

        result = load_config(config_file)
        assert result["security"]["webBindAddress"] == "127.0.0.1"
        assert result["camera"]["frameRate"] == 30

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test that missing config file raises FileNotFoundError."""
        missing_file = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError):
            load_config(missing_file)

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises json.JSONDecodeError."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ not valid json }")
        with pytest.raises(json.JSONDecodeError):
            load_config(config_file)

    def test_missing_required_section(self, tmp_path: Path) -> None:
        """Test that missing required section raises ConfigurationError."""
        config_file = tmp_path / "incomplete.json"
        config_data = {
            "security": {"webBindAddress": "127.0.0.1"},
            # Missing other required sections
        }
        config_file.write_text(json.dumps(config_data))
        with pytest.raises(ConfigurationError, match="Missing required config section"):
            load_config(config_file)


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self) -> None:
        """Test that Settings has sensible default values."""
        # These should be set even without config file
        assert Settings.webBindAddress is not None
        assert Settings.frameRate > 0
        assert Settings.testMode in (True, False)

    def test_settings_reload(self, tmp_path: Path) -> None:
        """Test that Settings can reload configuration."""
        # Create a test config
        config_file = tmp_path / "config.json"
        config_data = {
            "security": {"webBindAddress": "192.168.1.1", "webPort": 9090},
            "power": {"voltageIn": 12.0, "voltageOut": 11.4},
            "camera": {
                "width": 320,
                "height": 240,
                "frameRate": 15,
                "flippedImage": False,
            },
            "processing": {
                "scaledWidth": 80,
                "scaledHeight": 60,
                "processingThreads": 2,
                "minHuntColour": [0, 0, 0],
                "maxHuntColour": [255, 255, 255],
                "erodeSize": 3,
            },
            "control": {
                "motorSmoothing": 3,
                "positionP": 0.5,
                "positionI": 0.1,
                "positionD": 0.2,
                "changeP": 0.5,
                "changeI": 0.1,
                "changeD": 0.2,
                "clipI": 50,
            },
            "drive": {
                "steeringGain": 0.8,
                "steeringClip": 0.9,
                "steeringOffset": 0.1,
            },
            "debug": {"showFps": False, "testMode": False, "showImages": False},
            "safety": {
                "batteryStopVoltage": 10.0,
                "batteryWarningVoltage": 10.5,
                "watchdogTimeoutSeconds": 2.0,
                "emergencyStopEnabled": False,
            },
        }
        config_file.write_text(json.dumps(config_data))

        # Load the test config
        Settings._loaded = False
        Settings.load(config_file)

        assert Settings.webBindAddress == "192.168.1.1"
        assert Settings.frameRate == 15
        assert Settings.testMode is False
