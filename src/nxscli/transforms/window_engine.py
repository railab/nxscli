"""Shared window extraction and incremental scheduling logic."""

from typing import Sequence

import numpy as np

from nxscli.transforms.models import WindowConfig, WindowCursor


def normalize_window_config(
    window: int, hop: int | None = None
) -> WindowConfig:
    """Normalize window/hop values into a valid configuration."""
    win = max(2, int(window))
    if hop is None or int(hop) <= 0:
        hop_n = max(1, win // 4)
    else:
        hop_n = max(1, int(hop))
    return WindowConfig(window=win, hop=hop_n)


def should_recompute(
    total_count: int, cfg: WindowConfig, cursor: WindowCursor
) -> bool:
    """Return True when enough new samples arrived for next window step."""
    if total_count <= 0:
        return False
    if cursor.last_count == 0:
        cursor.last_count = total_count
        return True
    if total_count - cursor.last_count >= cfg.hop:
        cursor.last_count = total_count
        return True
    return False


def latest_window(series: Sequence[float], cfg: WindowConfig) -> np.ndarray:
    """Get latest signal window from an in-memory series."""
    arr = np.asarray(series, dtype=np.float64)
    if arr.size <= cfg.window:
        return arr
    return arr[-cfg.window :]
