"""Virtual channel manager and execution graph."""

from dataclasses import dataclass
from typing import Callable

from nxslib.dev import DeviceChannel

from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.models import (
    ChannelSpec,
    SampleValue,
    VirtualChannelSpec,
)
from nxscli.virtual.operators import (
    VirtualOperator,
    default_operator_registry,
)


@dataclass
class _CompiledVirtualChannel:
    """Internal node state for one virtual channel declaration."""

    spec: VirtualChannelSpec
    outputs: tuple[ChannelSpec, ...]
    output_ids: tuple[str, ...]
    operator: VirtualOperator


class VirtualChannelManager:
    """Manage virtual channel declarations and execution graph."""

    def __init__(
        self,
        operators: dict[str, Callable[[], VirtualOperator]] | None = None,
    ) -> None:
        """Initialize manager with operator registry."""
        self._operators = operators or default_operator_registry()
        self._channels: dict[str, ChannelSpec] = {}
        self._compiled: dict[str, _CompiledVirtualChannel] = {}
        self._output_owner: dict[str, str] = {}
        self._last_values: dict[str, SampleValue] = {}
        self._order: list[str] = []

    def add_physical_channel(self, spec: ChannelSpec | DeviceChannel) -> None:
        """Add physical channel metadata."""
        if isinstance(spec, DeviceChannel):
            spec = ChannelSpec.from_device_channel(spec)
        if spec.channel_id in self._channels:
            raise VirtualChannelError(
                f"Channel already exists: {spec.channel_id}"
            )
        self._channels[spec.channel_id] = spec

    def add_virtual_channel(
        self, spec: VirtualChannelSpec
    ) -> tuple[ChannelSpec, ...]:
        """Register one virtual channel and rebuild execution order."""
        if spec.channel_id in self._compiled:
            raise VirtualChannelError(
                f"Virtual channel already exists: {spec.channel_id}"
            )
        if spec.operator not in self._operators:
            raise VirtualChannelError(f"Unknown operator: {spec.operator}")
        if len(spec.inputs) == 0:
            raise VirtualChannelError(
                "Virtual channel requires at least one input"
            )

        input_specs: list[ChannelSpec] = []
        for input_id in spec.inputs:
            input_spec = self.channel_spec(input_id)
            if input_spec is None:
                raise VirtualChannelError(f"Unknown input channel: {input_id}")
            input_specs.append(input_spec)

        operator = self._operators[spec.operator]()
        operator.configure(spec, tuple(input_specs))
        outputs = operator.describe_outputs(spec)
        if len(outputs) == 0:
            raise VirtualChannelError(
                "Operator must provide at least one output"
            )

        output_ids = tuple(out.channel_id for out in outputs)
        for output in outputs:
            if output.channel_id in self._channels:
                raise VirtualChannelError(
                    f"Output channel already exists: {output.channel_id}"
                )

        self._compiled[spec.channel_id] = _CompiledVirtualChannel(
            spec=spec,
            outputs=outputs,
            output_ids=output_ids,
            operator=operator,
        )
        for output in outputs:
            self._channels[output.channel_id] = output
            self._output_owner[output.channel_id] = spec.channel_id
        self._rebuild_order()
        return outputs

    def channel_spec(self, channel_id: str) -> ChannelSpec | None:
        """Return channel metadata by ID."""
        return self._channels.get(channel_id)

    def channel_specs(self) -> tuple[ChannelSpec, ...]:
        """Return all physical and virtual channel specs."""
        return tuple(self._channels.values())

    def physical_channel_ids(self) -> tuple[str, ...]:
        """Return IDs of physical channels only."""
        return tuple(
            channel_id
            for channel_id in self._channels
            if channel_id not in self._output_owner
        )

    def required_physical_channel_ids(self) -> tuple[str, ...]:
        """Return physical channel IDs required by declared virtual graph."""
        required: dict[str, None] = {}
        for node_id in self._order:
            compiled = self._compiled[node_id]
            for input_id in compiled.spec.inputs:
                if input_id not in self._output_owner:
                    required[input_id] = None
        return tuple(required.keys())

    def process_sample(
        self, physical_values: dict[str, SampleValue]
    ) -> dict[str, SampleValue]:
        """Process one sample tick and return full channel map."""
        result: dict[str, SampleValue] = dict(physical_values)

        for channel_id in self._channels:
            if channel_id not in self._output_owner:
                if channel_id not in result:
                    raise VirtualChannelError(
                        f"Missing physical channel value: {channel_id}"
                    )

        for node_id in self._order:
            compiled = self._compiled[node_id]
            if not compiled.spec.enabled:
                continue
            inputs: list[SampleValue] = []
            for input_id in compiled.spec.inputs:
                if input_id not in result:
                    raise VirtualChannelError(
                        f"Input value not available: {input_id}"
                    )
                inputs.append(result[input_id])
            outputs = compiled.operator.process(tuple(inputs))
            if len(outputs) != len(compiled.output_ids):
                raise VirtualChannelError("Operator returned invalid outputs")
            for output_id, value in zip(compiled.output_ids, outputs):
                result[output_id] = value
        return result

    def process_update(
        self, channel_id: str, value: SampleValue
    ) -> dict[str, SampleValue]:
        """Process one physical channel update and return changed virtuals."""
        spec = self._channels.get(channel_id)
        if spec is None or channel_id in self._output_owner:
            raise VirtualChannelError(
                f"Unknown physical channel: {channel_id}"
            )

        if len(value) != spec.vdim:
            raise VirtualChannelError(
                f"Invalid sample vdim for {channel_id}: "
                f"expected {spec.vdim}, got {len(value)}"
            )

        self._last_values[channel_id] = value
        changed: dict[str, SampleValue] = {}
        for node_id in self._order:
            compiled = self._compiled[node_id]
            if not compiled.spec.enabled:
                continue
            if not all(
                inp in self._last_values for inp in compiled.spec.inputs
            ):
                continue
            inputs = tuple(
                self._last_values[inp] for inp in compiled.spec.inputs
            )
            outputs = compiled.operator.process(inputs)
            if len(outputs) != len(compiled.output_ids):
                raise VirtualChannelError("Operator returned invalid outputs")
            for output_id, out_value in zip(compiled.output_ids, outputs):
                self._last_values[output_id] = out_value
                changed[output_id] = out_value
        return changed

    def reset(self) -> None:
        """Reset all virtual operators."""
        self._last_values.clear()
        for compiled in self._compiled.values():
            compiled.operator.reset()

    def _rebuild_order(self) -> None:
        """Rebuild topological execution order with cycle detection."""
        visiting: set[str] = set()
        visited: set[str] = set()
        order: list[str] = []

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                raise VirtualChannelError("Virtual channel graph has a cycle")
            visiting.add(node)
            compiled = self._compiled[node]
            for input_id in compiled.spec.inputs:
                owner = self._output_owner.get(input_id)
                if owner is not None:
                    visit(owner)
            visiting.remove(node)
            visited.add(node)
            order.append(node)

        for node in self._compiled:
            visit(node)
        self._order = order
