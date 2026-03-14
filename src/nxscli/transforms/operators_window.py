"""Window-domain transform operators."""

from typing import Sequence

import numpy as np

from nxscli.transforms.models import (
    FftResult,
    HistogramResult,
    WindowCursor,
    XyResult,
)
from nxscli.transforms.window_engine import (
    latest_window,
    normalize_window_config,
    should_recompute,
)


def _weights(window_fn: str, size: int) -> np.ndarray:
    name = window_fn.lower()
    if name == "hann":
        return np.hanning(size)
    if name == "hamming":
        return np.hamming(size)
    if name == "blackman":
        return np.blackman(size)
    return np.ones(size, dtype=np.float64)


def fft_spectrum(
    samples: Sequence[float] | np.ndarray,
    *,
    sample_period: float = 1.0,
    window_fn: str = "hann",
) -> FftResult:
    """Compute one-sided FFT magnitude spectrum."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.size < 2:
        return FftResult(
            freq=np.asarray([], dtype=np.float64),
            amplitude=np.asarray([], dtype=np.float64),
        )
    weighted = arr * _weights(window_fn, int(arr.size))
    freq = np.fft.rfftfreq(int(weighted.size), d=float(sample_period))
    amp = np.abs(np.fft.rfft(weighted))
    return FftResult(
        freq=freq.astype(np.float64),
        amplitude=amp.astype(np.float64),
    )


def histogram_counts(
    samples: Sequence[float] | np.ndarray,
    *,
    bins: int,
    range_mode: str = "auto",
    value_range: tuple[float, float] | None = None,
) -> HistogramResult:
    """Compute histogram bin counts."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.size == 0:
        return HistogramResult(
            counts=np.asarray([], dtype=np.float64),
            edges=np.asarray([], dtype=np.float64),
        )

    hist_range = None
    if range_mode == "fixed":
        if value_range is None:
            raise ValueError(
                "value_range must be provided for fixed range_mode"
            )
        hist_range = (float(value_range[0]), float(value_range[1]))

    counts, edges = np.histogram(
        arr,
        bins=max(1, int(bins)),
        range=hist_range,
    )
    return HistogramResult(
        counts=counts.astype(np.float64),
        edges=edges.astype(np.float64),
    )


def xy_relation(
    x_samples: Sequence[float],
    y_samples: Sequence[float],
    *,
    window: int,
    align_policy: str = "truncate",
) -> XyResult:
    """Build XY relation from two sample series."""
    xa = np.asarray(x_samples, dtype=np.float64)
    ya = np.asarray(y_samples, dtype=np.float64)
    if align_policy != "truncate":
        raise ValueError("unsupported align_policy")
    size = min(int(xa.size), int(ya.size), max(2, int(window)))
    if size <= 0:
        return XyResult(
            x=np.asarray([], dtype=np.float64),
            y=np.asarray([], dtype=np.float64),
        )
    return XyResult(x=xa[-size:], y=ya[-size:])


def windowed_fft(
    series: Sequence[float],
    *,
    window: int,
    hop: int | None,
    cursor: WindowCursor,
    window_fn: str = "hann",
    total_count: int | None = None,
) -> FftResult | None:
    """Compute FFT only when hop criteria is satisfied."""
    cfg = normalize_window_config(window, hop)
    current = len(series) if total_count is None else int(total_count)
    if not should_recompute(current, cfg, cursor):
        return None
    arr = latest_window(series, cfg)
    return fft_spectrum(arr, window_fn=window_fn)


def windowed_histogram(
    series: Sequence[float],
    *,
    window: int,
    hop: int | None,
    bins: int,
    range_mode: str,
    cursor: WindowCursor,
    total_count: int | None = None,
    value_range: tuple[float, float] | None = None,
) -> HistogramResult | None:
    """Compute histogram only when hop criteria is satisfied."""
    cfg = normalize_window_config(window, hop)
    current = len(series) if total_count is None else int(total_count)
    if not should_recompute(current, cfg, cursor):
        return None
    arr = latest_window(series, cfg)
    return histogram_counts(
        arr,
        bins=bins,
        range_mode=range_mode,
        value_range=value_range,
    )


def windowed_xy(
    x_series: Sequence[float],
    y_series: Sequence[float],
    *,
    window: int,
    hop: int | None,
    align_policy: str,
    cursor: WindowCursor,
    total_count: int | None = None,
) -> XyResult | None:
    """Compute XY relation only when hop criteria is satisfied."""
    cfg = normalize_window_config(window, hop)
    if total_count is None:
        total = min(len(x_series), len(y_series))
    else:
        total = int(total_count)
    if not should_recompute(total, cfg, cursor):
        return None
    return xy_relation(
        x_series,
        y_series,
        window=cfg.window,
        align_policy=align_policy,
    )
