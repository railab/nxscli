import numpy as np
import pytest

from nxscli.transforms.models import WindowConfig, WindowCursor
from nxscli.transforms.operators_sample import apply_scale_offset, binary_op
from nxscli.transforms.operators_window import (
    fft_spectrum,
    histogram_counts,
    windowed_fft,
    windowed_histogram,
    windowed_xy,
    xy_relation,
)
from nxscli.transforms.window_engine import (
    latest_window,
    normalize_window_config,
    should_recompute,
)


def test_apply_scale_offset() -> None:
    arr = apply_scale_offset([1.0, 2.0, 3.0], scale=2.0, offset=-1.0)
    assert arr.tolist() == [1.0, 3.0, 5.0]


def test_binary_op_truncates_shorter_input() -> None:
    arr = binary_op([1.0, 2.0, 3.0], [10.0, 20.0], np.add)
    assert arr.tolist() == [11.0, 22.0]


def test_binary_op_empty_result() -> None:
    arr = binary_op([], [1.0], np.add)
    assert arr.tolist() == []


def test_fft_spectrum_nonempty() -> None:
    res = fft_spectrum([0.0, 1.0, 0.0, -1.0], window_fn="rect")
    assert int(res.freq.size) > 0
    assert int(res.amplitude.size) == int(res.freq.size)
    hamming = fft_spectrum([0.0, 1.0, 0.0, -1.0], window_fn="hamming")
    blackman = fft_spectrum([0.0, 1.0, 0.0, -1.0], window_fn="blackman")
    assert int(hamming.freq.size) > 0
    assert int(blackman.freq.size) > 0


def test_fft_spectrum_empty() -> None:
    res = fft_spectrum([1.0])
    assert res.freq.tolist() == []
    assert res.amplitude.tolist() == []


def test_histogram_counts_preserves_count() -> None:
    src = [0.0, 0.1, 0.2, 0.7, 0.9]
    res = histogram_counts(src, bins=3, range_mode="auto")
    assert int(res.counts.sum()) == len(src)
    assert int(res.edges.size) == 4


def test_histogram_counts_fixed_and_empty_and_error() -> None:
    fixed = histogram_counts(
        [0.0, 0.5], bins=2, range_mode="fixed", value_range=(0.0, 1.0)
    )
    assert int(fixed.counts.sum()) == 2
    empty = histogram_counts([], bins=2)
    assert empty.counts.tolist() == []
    with pytest.raises(ValueError):
        histogram_counts([0.0], bins=2, range_mode="fixed")


def test_xy_relation_truncate() -> None:
    res = xy_relation([1.0, 2.0, 3.0], [10.0, 20.0], window=64)
    assert res.x.tolist() == [2.0, 3.0]
    assert res.y.tolist() == [10.0, 20.0]


def test_xy_relation_errors_and_empty() -> None:
    res = xy_relation([], [], window=8)
    assert res.x.tolist() == []
    assert res.y.tolist() == []
    with pytest.raises(ValueError):
        xy_relation([1.0], [1.0], window=2, align_policy="pad")


def test_windowed_fft_hop_gating() -> None:
    cursor = WindowCursor()
    assert windowed_fft([1.0, 2.0], window=4, hop=2, cursor=cursor) is not None
    assert (
        windowed_fft([1.0, 2.0, 3.0], window=4, hop=2, cursor=cursor) is None
    )
    assert (
        windowed_fft([1.0, 2.0, 3.0, 4.0], window=4, hop=2, cursor=cursor)
        is not None
    )


def test_windowed_histogram_hop_gating() -> None:
    cursor = WindowCursor()
    assert (
        windowed_histogram(
            [0.0, 1.0],
            window=4,
            hop=3,
            bins=2,
            range_mode="auto",
            cursor=cursor,
        )
        is not None
    )
    assert (
        windowed_histogram(
            [0.0, 1.0, 2.0],
            window=4,
            hop=3,
            bins=2,
            range_mode="auto",
            cursor=cursor,
        )
        is None
    )


def test_windowed_xy_hop_gating() -> None:
    cursor = WindowCursor()
    assert (
        windowed_xy(
            [1.0, 2.0],
            [3.0, 4.0],
            window=16,
            hop=2,
            align_policy="truncate",
            cursor=cursor,
        )
        is not None
    )
    assert (
        windowed_xy(
            [1.0, 2.0, 3.0],
            [3.0, 4.0, 5.0],
            window=16,
            hop=2,
            align_policy="truncate",
            cursor=cursor,
        )
        is None
    )


def test_windowed_total_count_and_window_helpers() -> None:
    cfg = normalize_window_config(1, None)
    assert cfg.window >= 2
    assert cfg.hop >= 1
    cfg2 = normalize_window_config(8, 0)
    assert cfg2.hop == 2
    cfg3 = normalize_window_config(8, 3)
    assert cfg3.hop == 3

    cursor = WindowCursor()
    assert should_recompute(0, WindowConfig(window=4, hop=2), cursor) is False
    assert should_recompute(2, WindowConfig(window=4, hop=2), cursor) is True
    assert should_recompute(3, WindowConfig(window=4, hop=2), cursor) is False

    arr1 = latest_window([1.0, 2.0], WindowConfig(window=8, hop=2))
    assert arr1.tolist() == [1.0, 2.0]
    arr2 = latest_window([1.0, 2.0, 3.0], WindowConfig(window=2, hop=1))
    assert arr2.tolist() == [2.0, 3.0]

    cursor2 = WindowCursor()
    assert (
        windowed_xy(
            [1.0, 2.0],
            [3.0, 4.0],
            window=2,
            hop=2,
            align_policy="truncate",
            cursor=cursor2,
            total_count=2,
        )
        is not None
    )
