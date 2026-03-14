"""Tests for virtual data models helpers."""

from nxslib.dev import DeviceChannel, EDeviceChannelType

from nxscli.virtual.models import ChannelSpec, to_float


def test_channel_spec_from_device_channel() -> None:
    ch = DeviceChannel(7, int(EDeviceChannelType.FLOAT.value), 2, "temp")
    spec = ChannelSpec.from_device_channel(ch, data_kind="stats")
    assert spec.channel_id == "7"
    assert spec.name == "temp"
    assert spec.vdim == 2
    assert spec.data_kind == "stats"


def test_channel_spec_dtype_and_channel_id_parsing() -> None:
    spec = ChannelSpec(channel_id="v0", name="virt", dtype="int", vdim=1)
    assert spec.dtype == int(EDeviceChannelType.INT32.value)
    assert spec.device_channel.data.chan == -1

    spec2 = ChannelSpec(channel_id="3", name="x", dtype=9, vdim=1)
    assert spec2.dtype == 9
    assert spec2.device_channel.data.chan == 3
    spec3 = ChannelSpec(channel_id="4", name="y", dtype="unknown", vdim=1)
    assert spec3.dtype == int(EDeviceChannelType.FLOAT.value)
    spec4 = ChannelSpec(channel_id="5", name="z", dtype=object(), vdim=1)
    assert spec4.dtype == int(EDeviceChannelType.FLOAT.value)


def test_to_float_paths() -> None:
    assert to_float(1, 0.0) == 1.0
    assert to_float(1.5, 0.0) == 1.5
    assert to_float("2.5", 0.0) == 2.5
    assert to_float("bad", 7.0) == 7.0
    assert to_float(object(), 9.0) == 9.0
