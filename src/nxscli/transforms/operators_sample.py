"""Sample-domain transform operators."""

from typing import Callable, Sequence

import numpy as np


def apply_scale_offset(
    samples: Sequence[float], scale: float = 1.0, offset: float = 0.0
) -> np.ndarray:
    """Apply affine transform to scalar samples."""
    arr = np.asarray(samples, dtype=np.float64)
    return arr * float(scale) + float(offset)


def binary_op(
    left: Sequence[float],
    right: Sequence[float],
    op: Callable[[np.ndarray, np.ndarray], np.ndarray],
) -> np.ndarray:
    """Apply binary operation to aligned sample sequences."""
    la = np.asarray(left, dtype=np.float64)
    ra = np.asarray(right, dtype=np.float64)
    size = min(int(la.size), int(ra.size))
    if size <= 0:
        return np.asarray([], dtype=np.float64)
    return op(la[:size], ra[:size])
