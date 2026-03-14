"""Data models used by shared transform operators."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WindowConfig:
    """Windowed transform configuration."""

    window: int
    hop: int


@dataclass
class WindowCursor:
    """Incremental window-processing cursor."""

    last_count: int = 0


@dataclass(frozen=True)
class FftResult:
    """FFT result model."""

    freq: Any
    amplitude: Any


@dataclass(frozen=True)
class HistogramResult:
    """Histogram result model."""

    counts: Any
    edges: Any


@dataclass(frozen=True)
class XyResult:
    """XY relation result model."""

    x: Any
    y: Any
