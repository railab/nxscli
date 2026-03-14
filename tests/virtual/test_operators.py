"""Tests for virtual built-in operators."""

import math

import pytest

from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.models import ChannelSpec, VirtualChannelSpec
from nxscli.virtual.operators import (
    MathBinaryOperator,
    RunningStatsOperator,
    ScaleOffsetOperator,
    default_operator_registry,
)


def _spec(
    channel_id: str,
    operator: str,
    *,
    params: dict[str, object] | None = None,
) -> VirtualChannelSpec:
    return VirtualChannelSpec(
        channel_id=channel_id,
        name=channel_id,
        operator=operator,
        inputs=("0",),
        params=params or {},
    )


def test_scale_offset_operator() -> None:
    op = ScaleOffsetOperator()
    with pytest.raises(VirtualChannelError):
        op.configure(_spec("v0", "scale_offset"), ())
    op.configure(
        _spec("v0", "scale_offset", params={"scale": "2", "offset": "1"}),
        (ChannelSpec("0", "ch0", "float", 2),),
    )
    out = op.describe_outputs(_spec("v0", "scale_offset"))
    assert out[0].vdim == 2
    assert op.process(((1.0, 2.0),))[0] == (3.0, 5.0)
    op.reset()


def test_math_binary_operator_paths() -> None:
    op = MathBinaryOperator()
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "math_binary"),
            (ChannelSpec("0", "a", "float", 1),),
        )
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "math_binary"),
            (
                ChannelSpec("0", "a", "float", 1),
                ChannelSpec("1", "b", "float", 2),
            ),
        )
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "math_binary", params={"op": "bad"}),
            (
                ChannelSpec("0", "a", "float", 1),
                ChannelSpec("1", "b", "float", 1),
            ),
        )
    op.configure(
        _spec("v0", "math_binary", params={"op": "sub"}),
        (
            ChannelSpec("0", "a", "float", 1),
            ChannelSpec("1", "b", "float", 1),
        ),
    )
    assert op.process(((4.0,), (1.5,)))[0] == (2.5,)
    op.reset()


def test_running_stats_operator_paths() -> None:
    op = RunningStatsOperator()
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "stats_running"),
            (),
        )
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "stats_running"),
            (ChannelSpec("0", "a", "float", 0),),
        )
    with pytest.raises(VirtualChannelError):
        op.configure(
            _spec("v0", "stats_running", params={"bad": 1}),
            (ChannelSpec("0", "a", "float", 1),),
        )

    op.configure(
        _spec("v0", "stats_running"),
        (ChannelSpec("0", "a", "float", 1),),
    )
    outs = op.describe_outputs(_spec("v0", "stats_running"))
    assert len(outs) == 4
    minv, maxv, avgv, rmsv = op.process(((2.0,),))
    assert minv == (2.0,)
    assert maxv == (2.0,)
    assert avgv == (2.0,)
    assert rmsv == (2.0,)
    minv, maxv, avgv, rmsv = op.process(((4.0,),))
    assert minv == (2.0,)
    assert maxv == (4.0,)
    assert avgv == (3.0,)
    assert math.isclose(rmsv[0], math.sqrt((4.0 + 16.0) / 2.0))
    minv, maxv, _, _ = op.process(((1.0,),))
    assert minv == (1.0,)
    assert maxv == (4.0,)
    with pytest.raises(VirtualChannelError):
        op.process(((1.0, 2.0),))
    op.reset()


def test_default_registry_factories() -> None:
    reg = default_operator_registry()
    assert callable(reg["scale_offset"])
    assert callable(reg["math_binary"])
    assert callable(reg["stats_running"])
