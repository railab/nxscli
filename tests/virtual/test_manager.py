"""Tests for virtual operator graph manager."""

import pytest

from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.manager import VirtualChannelManager
from nxscli.virtual.models import ChannelSpec, VirtualChannelSpec
from nxscli.virtual.operators import default_operator_registry


def test_default_registry_contains_builtin_ops() -> None:
    reg = default_operator_registry()
    assert set(reg) == {
        "scale_offset",
        "math_binary",
        "stats_running",
    }


def test_virtual_manager_pipeline() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_physical_channel(ChannelSpec("1", "ch1", "float", 1))

    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v0",
            name="scaled",
            operator="scale_offset",
            inputs=("0",),
            params={"scale": 2.0, "offset": 1.0},
        )
    )
    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v1",
            name="sum",
            operator="math_binary",
            inputs=("v0", "1"),
            params={"op": "add"},
        )
    )

    out = mgr.process_sample({"0": (1.0,), "1": (3.0,)})
    assert out["v0"] == (3.0,)
    assert out["v1"] == (6.0,)
    assert mgr.required_physical_channel_ids() == ("0", "1")


def test_virtual_manager_errors() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))

    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(
            VirtualChannelSpec(
                channel_id="v0",
                name="bad",
                operator="unknown",
                inputs=("0",),
            )
        )

    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v0",
            name="ok",
            operator="scale_offset",
            inputs=("0",),
        )
    )
    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(
            VirtualChannelSpec(
                channel_id="v0",
                name="dup",
                operator="scale_offset",
                inputs=("0",),
            )
        )


def test_virtual_manager_more_error_paths() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    with pytest.raises(VirtualChannelError):
        mgr.add_physical_channel(ChannelSpec("0", "dup", "float", 1))

    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(
            VirtualChannelSpec(
                channel_id="v0",
                name="noin",
                operator="scale_offset",
                inputs=(),
            )
        )
    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(
            VirtualChannelSpec(
                channel_id="v0",
                name="unknown-input",
                operator="scale_offset",
                inputs=("9",),
            )
        )

    with pytest.raises(VirtualChannelError):
        mgr.process_update("v0", (1.0,))
    with pytest.raises(VirtualChannelError):
        mgr.process_update("0", (1.0, 2.0))


def test_virtual_manager_disabled_and_reset() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v0",
            name="scaled",
            operator="scale_offset",
            inputs=("0",),
            enabled=False,
        )
    )
    changed = mgr.process_update("0", (1.0,))
    assert changed == {}
    out = mgr.process_sample({"0": (1.0,)})
    assert out == {"0": (1.0,)}
    assert mgr.channel_spec("0") is not None
    assert len(mgr.channel_specs()) >= 1
    assert mgr.physical_channel_ids() == ("0",)
    mgr.reset()


def test_virtual_manager_cycle_detection() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v0",
            name="scaled",
            operator="scale_offset",
            inputs=("0",),
        )
    )
    # Force cycle in compiled graph and verify detector.
    compiled = mgr._compiled["v0"]
    mgr._compiled["v0"] = type(compiled)(
        spec=VirtualChannelSpec(
            channel_id="v0",
            name="scaled",
            operator="scale_offset",
            inputs=("v0",),
        ),
        outputs=compiled.outputs,
        output_ids=compiled.output_ids,
        operator=compiled.operator,
    )
    with pytest.raises(VirtualChannelError):
        mgr._rebuild_order()


class _NoOutputs:
    def configure(self, spec, inputs) -> None:
        del spec, inputs

    def describe_outputs(self, spec):
        del spec
        return ()

    def process(self, inputs):
        del inputs
        return ()

    def reset(self) -> None:
        return


class _BadOutLen:
    def configure(self, spec, inputs) -> None:
        del spec, inputs

    def describe_outputs(self, spec):
        return (
            ChannelSpec(
                channel_id=spec.channel_id,
                name=spec.name,
                dtype="float",
                vdim=1,
            ),
        )

    def process(self, inputs):
        del inputs
        return ((1.0,), (2.0,))

    def reset(self) -> None:
        return


class _Collide:
    def configure(self, spec, inputs) -> None:
        del spec, inputs

    def describe_outputs(self, spec):
        del spec
        return (ChannelSpec("0", "dup", "float", 1),)

    def process(self, inputs):
        del inputs
        return ((1.0,),)

    def reset(self) -> None:
        return


def test_virtual_manager_no_outputs_and_collide() -> None:
    assert _NoOutputs().process(()) == ()
    _NoOutputs().reset()
    assert _Collide().process(()) == ((1.0,),)
    _Collide().reset()
    mgr = VirtualChannelManager(operators={"no": _NoOutputs, "col": _Collide})
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(VirtualChannelSpec("v0", "x", "no", ("0",)))
    with pytest.raises(VirtualChannelError):
        mgr.add_virtual_channel(VirtualChannelSpec("v0", "x", "col", ("0",)))


def test_virtual_manager_bad_output_len() -> None:
    _BadOutLen().reset()
    mgr2 = VirtualChannelManager(operators={"badlen": _BadOutLen})
    mgr2.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr2.add_virtual_channel(VirtualChannelSpec("v0", "x", "badlen", ("0",)))
    with pytest.raises(VirtualChannelError):
        mgr2.process_update("0", (1.0,))
    with pytest.raises(VirtualChannelError):
        mgr2.process_sample({})


def test_virtual_manager_process_sample_missing_input() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_physical_channel(ChannelSpec("1", "ch1", "float", 1))
    mgr.add_virtual_channel(
        VirtualChannelSpec(
            channel_id="v1",
            name="sum",
            operator="math_binary",
            inputs=("0", "1"),
            params={"op": "add"},
        )
    )
    with pytest.raises(VirtualChannelError):
        mgr.process_sample({"0": (1.0,)})


def test_virtual_manager_process_sample_invalid_outputs_len() -> None:
    mgr = VirtualChannelManager(operators={"badlen": _BadOutLen})
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_virtual_channel(VirtualChannelSpec("v0", "x", "badlen", ("0",)))
    with pytest.raises(VirtualChannelError):
        mgr.process_sample({"0": (1.0,)})


def test_virtual_manager_process_sample_missing_runtime_input() -> None:
    mgr = VirtualChannelManager()
    mgr.add_physical_channel(ChannelSpec("0", "ch0", "float", 1))
    mgr.add_virtual_channel(
        VirtualChannelSpec("v0", "x", "scale_offset", ("0",))
    )
    compiled = mgr._compiled["v0"]
    mgr._compiled["v0"] = type(compiled)(
        spec=VirtualChannelSpec("v0", "x", "scale_offset", ("ghost",)),
        outputs=compiled.outputs,
        output_ids=compiled.output_ids,
        operator=compiled.operator,
    )
    with pytest.raises(VirtualChannelError):
        mgr.process_sample({"0": (1.0,)})
