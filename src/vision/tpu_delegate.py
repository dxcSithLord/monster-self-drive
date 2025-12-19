"""TPU Delegate - Google Coral Edge TPU hardware abstraction.

This module provides a hardware abstraction layer for the Google Coral
Edge TPU USB Accelerator, enabling hardware-accelerated ML inference
for object detection.

Features:
- Automatic TPU detection and initialization
- Graceful fallback to CPU inference when TPU unavailable
- Model loading with TPU/CPU interpreter selection
- Runtime performance monitoring

Usage:
    delegate = TPUDelegate()
    if delegate.is_available():
        interpreter = delegate.make_interpreter("model_edgetpu.tflite")
    else:
        interpreter = delegate.make_interpreter("model.tflite", use_tpu=False)

Hardware Setup (Raspberry Pi):
    # Add Coral repository
    echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
        sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update

    # Install Edge TPU runtime
    sudo apt-get install libedgetpu1-std

    # Python bindings (from Coral repo)
    pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TPUBackend(Enum):
    """Available inference backends."""

    CORAL_TPU = auto()  # Google Coral Edge TPU
    CPU_TFLITE = auto()  # TensorFlow Lite CPU
    NONE = auto()  # No inference available


@dataclass
class TPUStats:
    """TPU performance statistics."""

    backend: TPUBackend = TPUBackend.NONE
    inference_count: int = 0
    total_inference_time_ms: float = 0.0
    last_inference_time_ms: float = 0.0
    model_path: str = ""
    input_shape: tuple = ()

    @property
    def average_inference_time_ms(self) -> float:
        """Average inference time in milliseconds."""
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_time_ms / self.inference_count

    @property
    def estimated_fps(self) -> float:
        """Estimated frames per second based on average inference time."""
        avg = self.average_inference_time_ms
        if avg <= 0:
            return 0.0
        return 1000.0 / avg


@dataclass
class TPUDelegate:
    """Hardware abstraction for Google Coral Edge TPU.

    Provides automatic detection and initialization of Coral TPU hardware,
    with graceful fallback to CPU inference when TPU is unavailable.

    Attributes:
        stats: Performance statistics for the current session.
        _tpu_available: Whether TPU hardware was detected.
        _tflite_available: Whether TFLite runtime is available.
        _interpreter: Current TFLite interpreter instance.
    """

    stats: TPUStats = field(default_factory=TPUStats)
    _tpu_available: bool | None = field(default=None, repr=False)
    _tflite_available: bool | None = field(default=None, repr=False)
    _interpreter: Any = field(default=None, repr=False)
    _pycoral_module: Any = field(default=None, repr=False)
    _tflite_module: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize and detect available backends."""
        self._detect_backends()

    def _detect_backends(self) -> None:
        """Detect available inference backends."""
        # Try importing pycoral for Coral TPU
        try:
            from pycoral.utils import edgetpu

            self._pycoral_module = edgetpu
            # Check if TPU devices are actually connected
            devices = edgetpu.list_edge_tpus()
            self._tpu_available = len(devices) > 0
            if self._tpu_available:
                logger.info(f"Coral TPU detected: {devices}")
            else:
                logger.info("Coral TPU library available but no device connected")
        except ImportError:
            logger.info("pycoral not installed - Coral TPU unavailable")
            self._tpu_available = False
        except Exception as e:
            logger.warning(f"Error detecting Coral TPU: {e}")
            self._tpu_available = False

        # Try importing TFLite runtime for CPU fallback
        try:
            import tflite_runtime.interpreter as tflite

            self._tflite_module = tflite
            self._tflite_available = True
            logger.info("TFLite runtime available for CPU inference")
        except ImportError:
            # Try ai-edge-litert as alternative
            try:
                from ai_edge_litert import interpreter as litert

                self._tflite_module = litert
                self._tflite_available = True
                logger.info("ai-edge-litert available for CPU inference")
            except ImportError:
                logger.info("No TFLite runtime available - CPU inference unavailable")
                self._tflite_available = False

    def is_available(self) -> bool:
        """Check if any inference backend is available.

        Returns:
            True if TPU or CPU inference is possible.
        """
        return bool(self._tpu_available or self._tflite_available)

    def is_tpu_available(self) -> bool:
        """Check if Coral TPU is available.

        Returns:
            True if Coral TPU is connected and functional.
        """
        return bool(self._tpu_available)

    def is_cpu_available(self) -> bool:
        """Check if CPU TFLite inference is available.

        Returns:
            True if TFLite runtime is installed.
        """
        return bool(self._tflite_available)

    def get_backend(self) -> TPUBackend:
        """Get the best available backend.

        Returns:
            The most performant available backend.
        """
        if self._tpu_available:
            return TPUBackend.CORAL_TPU
        elif self._tflite_available:
            return TPUBackend.CPU_TFLITE
        return TPUBackend.NONE

    def make_interpreter(
        self, model_path: str | Path, use_tpu: bool | None = None
    ) -> Any:
        """Create a TFLite interpreter for the given model.

        Args:
            model_path: Path to the TFLite model file.
            use_tpu: Force TPU (True), CPU (False), or auto-detect (None).

        Returns:
            A TFLite interpreter ready for inference.

        Raises:
            FileNotFoundError: If the model file doesn't exist.
            RuntimeError: If no inference backend is available.
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Determine which backend to use
        if use_tpu is None:
            use_tpu = self._tpu_available and self._is_edgetpu_model(model_path)

        if use_tpu and self._tpu_available:
            return self._make_tpu_interpreter(model_path)
        elif self._tflite_available:
            return self._make_cpu_interpreter(model_path)
        else:
            raise RuntimeError("No inference backend available")

    def _is_edgetpu_model(self, model_path: Path) -> bool:
        """Check if a model is compiled for Edge TPU.

        Args:
            model_path: Path to the model file.

        Returns:
            True if the model filename suggests Edge TPU compilation.
        """
        name = model_path.name.lower()
        return "edgetpu" in name or "_tpu" in name

    def _make_tpu_interpreter(self, model_path: Path) -> Any:
        """Create a Coral TPU interpreter.

        Args:
            model_path: Path to the Edge TPU model.

        Returns:
            Interpreter configured for TPU execution.
        """
        logger.info(f"Loading model on Coral TPU: {model_path}")
        interpreter = self._pycoral_module.make_interpreter(str(model_path))
        interpreter.allocate_tensors()

        # Update stats
        self.stats.backend = TPUBackend.CORAL_TPU
        self.stats.model_path = str(model_path)
        self._update_input_shape(interpreter)

        self._interpreter = interpreter
        return interpreter

    def _make_cpu_interpreter(self, model_path: Path) -> Any:
        """Create a CPU TFLite interpreter.

        Args:
            model_path: Path to the TFLite model.

        Returns:
            Interpreter configured for CPU execution.
        """
        logger.info(f"Loading model on CPU: {model_path}")

        # Handle different TFLite runtime APIs
        if hasattr(self._tflite_module, "Interpreter"):
            interpreter = self._tflite_module.Interpreter(model_path=str(model_path))
        else:
            # Fallback for different API versions
            interpreter = self._tflite_module.Interpreter(str(model_path))

        interpreter.allocate_tensors()

        # Update stats
        self.stats.backend = TPUBackend.CPU_TFLITE
        self.stats.model_path = str(model_path)
        self._update_input_shape(interpreter)

        self._interpreter = interpreter
        return interpreter

    def _update_input_shape(self, interpreter: Any) -> None:
        """Update stats with model input shape.

        Args:
            interpreter: The TFLite interpreter.
        """
        try:
            input_details = interpreter.get_input_details()
            if input_details:
                self.stats.input_shape = tuple(input_details[0]["shape"])
        except Exception as e:
            logger.warning(f"Could not get input shape: {e}")

    def invoke(self, interpreter: Any | None = None) -> float:
        """Run inference and return timing.

        Args:
            interpreter: The interpreter to use, or the last created one.

        Returns:
            Inference time in milliseconds.

        Raises:
            RuntimeError: If no interpreter is available.
        """
        if interpreter is None:
            interpreter = self._interpreter
        if interpreter is None:
            raise RuntimeError("No interpreter available - call make_interpreter first")

        start = time.perf_counter()
        interpreter.invoke()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Update stats
        self.stats.inference_count += 1
        self.stats.total_inference_time_ms += elapsed_ms
        self.stats.last_inference_time_ms = elapsed_ms

        return elapsed_ms

    def get_input_details(self, interpreter: Any | None = None) -> list[dict]:
        """Get input tensor details.

        Args:
            interpreter: The interpreter to query.

        Returns:
            List of input tensor details.
        """
        if interpreter is None:
            interpreter = self._interpreter
        if interpreter is None:
            return []
        return interpreter.get_input_details()

    def get_output_details(self, interpreter: Any | None = None) -> list[dict]:
        """Get output tensor details.

        Args:
            interpreter: The interpreter to query.

        Returns:
            List of output tensor details.
        """
        if interpreter is None:
            interpreter = self._interpreter
        if interpreter is None:
            return []
        return interpreter.get_output_details()

    def list_tpus(self) -> list[str]:
        """List connected Coral TPU devices.

        Returns:
            List of TPU device identifiers.
        """
        if not self._tpu_available or self._pycoral_module is None:
            return []
        try:
            return self._pycoral_module.list_edge_tpus()
        except Exception:
            return []

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self.stats.inference_count = 0
        self.stats.total_inference_time_ms = 0.0
        self.stats.last_inference_time_ms = 0.0


# Singleton instance for global access
_global_delegate: TPUDelegate | None = None


def get_tpu_delegate() -> TPUDelegate:
    """Get the global TPU delegate instance.

    Returns:
        The shared TPUDelegate instance.
    """
    global _global_delegate
    if _global_delegate is None:
        _global_delegate = TPUDelegate()
    return _global_delegate


def is_coral_available() -> bool:
    """Quick check if Coral TPU is available.

    Returns:
        True if Coral TPU can be used for inference.
    """
    return get_tpu_delegate().is_tpu_available()
