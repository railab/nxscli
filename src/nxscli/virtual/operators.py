"""Built-in virtual operators."""

import math
from typing import Callable, Protocol

from nxslib.dev import EDeviceChannelType

from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.models import (
    ChannelSpec,
    SampleValue,
    VirtualChannelSpec,
    to_float,
)


class VirtualOperator(Protocol):
    """Protocol implemented by virtual-channel operators."""

    def configure(
        self,
        spec: VirtualChannelSpec,
        inputs: tuple[ChannelSpec, ...],
    ) -> None:
        """Validate and store operator configuration."""

    def describe_outputs(
        self, spec: VirtualChannelSpec
    ) -> tuple[ChannelSpec, ...]:
        """Return output channel metadata."""

    def process(
        self, inputs: tuple[SampleValue, ...]
    ) -> tuple[SampleValue, ...]:
        """Process one sample tick."""

    def reset(self) -> None:
        """Reset internal operator state."""


class ScaleOffsetOperator:
    """Apply ``out = in * scale + offset`` element-wise."""

    def __init__(self) -> None:
        """Initialize defaults."""
        self._scale = 1.0
        self._offset = 0.0
        self._vdim = 1

    def configure(
        self,
        spec: VirtualChannelSpec,
        inputs: tuple[ChannelSpec, ...],
    ) -> None:
        """Validate inputs and parse parameters."""
        if len(inputs) != 1:
            raise VirtualChannelError("scale_offset expects exactly one input")
        self._vdim = inputs[0].vdim
        self._scale = to_float(spec.params.get("scale", 1.0), 1.0)
        self._offset = to_float(spec.params.get("offset", 0.0), 0.0)

    def describe_outputs(
        self, spec: VirtualChannelSpec
    ) -> tuple[ChannelSpec, ...]:
        """Describe single transformed output."""
        return (
            ChannelSpec(
                channel_id=spec.channel_id,
                name=spec.name,
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
            ),
        )

    def process(
        self, inputs: tuple[SampleValue, ...]
    ) -> tuple[SampleValue, ...]:
        """Apply scale/offset for one sample tick."""
        src = inputs[0]
        return (tuple((x * self._scale) + self._offset for x in src),)

    def reset(self) -> None:
        """Stateless operator reset."""
        return


class MathBinaryOperator:
    """Element-wise binary math operation."""

    _OPS: dict[str, Callable[[float, float], float]] = {
        "add": lambda a, b: a + b,
        "sub": lambda a, b: a - b,
        "mul": lambda a, b: a * b,
        "div": lambda a, b: a / b,
        "min": lambda a, b: a if a < b else b,
        "max": lambda a, b: a if a > b else b,
    }

    def __init__(self) -> None:
        """Initialize defaults."""
        self._vdim = 1
        self._op: Callable[[float, float], float] = self._OPS["add"]

    def configure(
        self,
        spec: VirtualChannelSpec,
        inputs: tuple[ChannelSpec, ...],
    ) -> None:
        """Validate inputs and operation kind."""
        if len(inputs) != 2:
            raise VirtualChannelError("math_binary expects exactly two inputs")
        if inputs[0].vdim != inputs[1].vdim:
            raise VirtualChannelError("math_binary inputs must have same vdim")
        op_name = str(spec.params.get("op", "add"))
        if op_name not in self._OPS:
            raise VirtualChannelError(f"Unsupported math operation: {op_name}")
        self._op = self._OPS[op_name]
        self._vdim = inputs[0].vdim

    def describe_outputs(
        self, spec: VirtualChannelSpec
    ) -> tuple[ChannelSpec, ...]:
        """Describe single math output."""
        return (
            ChannelSpec(
                channel_id=spec.channel_id,
                name=spec.name,
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
            ),
        )

    def process(
        self, inputs: tuple[SampleValue, ...]
    ) -> tuple[SampleValue, ...]:
        """Apply selected binary operation for one sample tick."""
        left, right = inputs
        out = tuple(self._op(a, b) for a, b in zip(left, right))
        return (out,)

    def reset(self) -> None:
        """Stateless operator reset."""
        return


class RunningStatsOperator:
    """Track running ``min,max,avg,rms`` and emit separate output streams."""

    def __init__(self) -> None:
        """Initialize running stats state."""
        self.reset()

    def configure(
        self,
        spec: VirtualChannelSpec,
        inputs: tuple[ChannelSpec, ...],
    ) -> None:
        """Validate one input and initialize per-dimension state."""
        if len(inputs) != 1:
            raise VirtualChannelError(
                "stats_running expects exactly one input"
            )
        if inputs[0].vdim <= 0:
            raise VirtualChannelError("stats_running requires non-empty input")
        if bool(spec.params):
            raise VirtualChannelError("stats_running does not accept params")
        vdim = inputs[0].vdim
        self.reset()
        self._vdim = vdim
        self._sum = [0.0 for _ in range(vdim)]
        self._sum_sq = [0.0 for _ in range(vdim)]
        self._min = [0.0 for _ in range(vdim)]
        self._max = [0.0 for _ in range(vdim)]

    def describe_outputs(
        self, spec: VirtualChannelSpec
    ) -> tuple[ChannelSpec, ...]:
        """Describe four stat output streams."""
        return (
            ChannelSpec(
                channel_id=f"{spec.channel_id}.min",
                name=f"{spec.name}_min",
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
                data_kind="stats",
            ),
            ChannelSpec(
                channel_id=f"{spec.channel_id}.max",
                name=f"{spec.name}_max",
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
                data_kind="stats",
            ),
            ChannelSpec(
                channel_id=f"{spec.channel_id}.avg",
                name=f"{spec.name}_avg",
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
                data_kind="stats",
            ),
            ChannelSpec(
                channel_id=f"{spec.channel_id}.rms",
                name=f"{spec.name}_rms",
                dtype=EDeviceChannelType.FLOAT.value,
                vdim=self._vdim,
                data_kind="stats",
            ),
        )

    def process(
        self, inputs: tuple[SampleValue, ...]
    ) -> tuple[SampleValue, ...]:
        """Update and return min/max/avg/rms outputs."""
        values = inputs[0]
        if len(values) != self._vdim:
            raise VirtualChannelError("stats_running input vdim mismatch")

        if self._count == 0:
            self._min = list(values)
            self._max = list(values)
        else:
            for i, value in enumerate(values):
                if value < self._min[i]:
                    self._min[i] = value
                if value > self._max[i]:
                    self._max[i] = value

        self._count += 1
        for i, value in enumerate(values):
            self._sum[i] += value
            self._sum_sq[i] += value * value

        avg = tuple(total / self._count for total in self._sum)
        rms = tuple(math.sqrt(total / self._count) for total in self._sum_sq)
        return (tuple(self._min), tuple(self._max), avg, rms)

    def reset(self) -> None:
        """Reset running counters and accumulators."""
        self._vdim = 1
        self._count = 0
        self._sum = [0.0]
        self._sum_sq = [0.0]
        self._min = [0.0]
        self._max = [0.0]


def default_operator_registry() -> dict[str, Callable[[], VirtualOperator]]:
    """Return built-in virtual-channel operator factories."""
    return {
        "scale_offset": ScaleOffsetOperator,
        "math_binary": MathBinaryOperator,
        "stats_running": RunningStatsOperator,
    }
