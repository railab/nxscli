"""Tests for shared virtual runtime provider."""

import queue

import numpy as np
import pytest
from nxslib.dev import Device, DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.channelref import ChannelRef
from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.runtime import VirtualStreamRuntime
from nxscli.virtual.services import get_runtime


class _FakeRegistry:
    def __init__(self) -> None:
        self._services = {}
        self.providers = []

    def service_get(self, name: str):
        return self._services.get(name)

    def service_set(self, name: str, service) -> None:
        self._services[name] = service

    def stream_provider_add(self, provider) -> None:
        self.providers.append(provider)


class _FakeNxscope:
    def __init__(self) -> None:
        channels = [
            DeviceChannel(0, 10, 1, "ch0"),
            DeviceChannel(1, 10, 1, "ch1"),
        ]
        self.dev = Device(2, 0, 0, channels)
        self._channels = {0: channels[0], 1: channels[1]}
        self._subs: dict[int, list[queue.Queue[list[DNxscopeStreamBlock]]]] = {
            0: [],
            1: [],
        }

    def dev_channel_get(self, chid: int):
        return self._channels.get(chid)

    def stream_sub(self, chan: int):
        subq = queue.Queue()
        self._subs[chan].append(subq)
        return subq

    def stream_unsub(self, subq) -> None:
        for chan in self._subs:
            if subq in self._subs[chan]:
                self._subs[chan].remove(subq)
                return


class _FakeNxscopeSparse(_FakeNxscope):
    def dev_channel_get(self, chid: int):
        if chid == 1:
            return None
        return super().dev_channel_get(chid)


def test_runtime_shared_provider() -> None:
    reg = _FakeRegistry()
    rt1 = get_runtime(reg)
    rt2 = get_runtime(reg)
    assert rt1 is rt2
    assert len(reg.providers) == 1


def test_runtime_streams_virtual_blocks() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()

    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="math_binary",
        inputs=("0", "1"),
        params={"op": "add"},
    )

    runtime.on_connect(fake)
    outq = runtime.stream_sub(ChannelRef.virtual(0))
    assert outq is not None

    runtime.on_stream_start()

    b0 = DNxscopeStreamBlock(
        data=np.asarray([[1.0]], dtype=np.float64), meta=None
    )
    b1 = DNxscopeStreamBlock(
        data=np.asarray([[2.0]], dtype=np.float64), meta=None
    )
    fake._subs[0][0].put([b0])
    runtime._thread_common()
    fake._subs[1][0].put([b1])
    runtime._thread_common()

    out = outq.get(block=True, timeout=0.2)
    assert isinstance(out[0], DNxscopeStreamBlock)
    assert out[0].data.shape == (1, 1)
    assert float(out[0].data[0, 0]) == 3.0

    runtime.on_stream_stop()
    runtime.on_disconnect()


def test_runtime_streams_from_1d_blocks() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()

    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={"scale": 2.0, "offset": 1.0},
    )

    runtime.on_connect(fake)
    outq = runtime.stream_sub(ChannelRef.virtual(0))
    assert outq is not None
    runtime.on_stream_start()

    # vdim=1 payload can arrive as 1D array
    b0 = DNxscopeStreamBlock(
        data=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
        meta=None,
    )
    fake._subs[0][0].put([b0])
    runtime._thread_common()

    out = outq.get(block=True, timeout=0.2)
    assert isinstance(out[0], DNxscopeStreamBlock)
    assert out[0].data.shape == (3, 1)
    assert float(out[0].data[0, 0]) == 3.0
    assert float(out[0].data[1, 0]) == 5.0
    assert float(out[0].data[2, 0]) == 7.0

    runtime.on_stream_stop()
    runtime.on_disconnect()


def test_runtime_guard_paths_and_clear() -> None:
    runtime = VirtualStreamRuntime()
    runtime.on_stream_start()  # no nxscope
    runtime.on_stream_stop()  # not started
    runtime.on_disconnect()  # no connection
    runtime.clear()
    assert runtime.declared() == ()
    runtime._thread_common()


def test_runtime_alias_and_duplicate_paths() -> None:
    runtime = VirtualStreamRuntime()
    with pytest.raises(VirtualChannelError):
        runtime.add_virtual_channel(
            channel_id=-1,
            name="bad",
            operator="scale_offset",
            inputs=("0",),
            params={},
        )

    runtime.add_virtual_channel(
        channel_id=10,
        name="v10",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    with pytest.raises(VirtualChannelError):
        runtime.add_virtual_channel(
            channel_id=10,
            name="dup",
            operator="scale_offset",
            inputs=("0",),
            params={},
        )
    with pytest.raises(VirtualChannelError):
        runtime.add_virtual_channel(
            channel_id=8,
            name="dup-alias",
            operator="stats_running",
            inputs=("0",),
            params={},
        )
    with pytest.raises(VirtualChannelError):
        runtime._normalize_input_token("vbad")


def test_runtime_channel_and_sub_paths() -> None:
    runtime = VirtualStreamRuntime()
    assert runtime.channel_get(ChannelRef.physical(0)) is None
    assert runtime.stream_sub(ChannelRef.physical(0)) is None
    assert runtime.stream_unsub(queue.Queue()) is False
    assert runtime.channel_list() == ()
    assert runtime._normalize_input_token("v01") == "v1"


def test_runtime_stats_aliases_and_subscribe_unknown() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()
    runtime.add_virtual_channel(
        channel_id=20,
        name="stats",
        operator="stats_running",
        inputs=("0",),
        params={},
    )
    runtime.on_connect(fake)
    # First alias exists, unknown alias does not.
    sub = runtime.stream_sub(ChannelRef.virtual(20))
    assert sub is not None
    assert runtime.stream_sub(ChannelRef.virtual(99)) is None
    assert runtime.stream_unsub(sub) is True
    runtime.on_disconnect()


def test_runtime_rebuild_mismatch_and_collect_skip() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()
    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    # Force mismatched declared output ids.
    dec = runtime._declared[0]
    runtime._declared[0] = type(dec)(
        spec=dec.spec,
        output_ids=("bad",),
        aliases=dec.aliases,
        aliased_names=dec.aliased_names,
    )
    with pytest.raises(VirtualChannelError):
        runtime.on_connect(fake)

    # Restore and connect.
    runtime = VirtualStreamRuntime()
    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    runtime.on_connect(fake)
    out = runtime._collect_output_rows(
        0,
        [
            DNxscopeStreamBlock(
                data=np.asarray([], dtype=np.float64), meta=None
            )
        ],
    )
    assert out == {}
    # channel id mismatch path in collect-update
    out2 = runtime._collect_output_rows(
        9,
        [
            DNxscopeStreamBlock(
                data=np.asarray([[1.0]], dtype=np.float64), meta=None
            )
        ],
    )
    assert out2 == {}
    runtime._output_id_to_alias["v0"] = "missing"
    batches = runtime._build_output_blocks({"missing": [(1.0,)]})
    assert batches == {}
    runtime._output_id_to_alias["v0"] = "v0"
    bad = DNxscopeStreamBlock(
        data=np.asarray([["bad"]], dtype=object), meta=None
    )
    assert runtime._collect_output_rows(0, [bad]) == {}
    runtime._output_id_to_alias.clear()
    good = DNxscopeStreamBlock(
        data=np.asarray([[1.0]], dtype=np.float64), meta=None
    )
    assert runtime._collect_output_rows(0, [good]) == {}
    assert runtime._to_sample("bad") is None
    assert runtime._normalize_input_token("1") == "1"
    runtime.on_disconnect()


def test_runtime_start_stop_transitions() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()
    runtime.on_connect(fake)
    runtime.on_stream_start()  # no declarations
    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    runtime.on_stream_start()
    runtime.on_stream_start()  # already started
    runtime.on_stream_stop()
    runtime.on_stream_stop()  # already stopped


def test_runtime_rebuild_skips_missing_device_channels() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscopeSparse()
    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    runtime.on_connect(fake)
    assert runtime.channel_list()
    runtime._started = True
    runtime._nxscope = None
    runtime.on_stream_stop()


def test_runtime_stream_unsub_branch_paths() -> None:
    runtime = VirtualStreamRuntime()
    fake = _FakeNxscope()
    runtime.add_virtual_channel(
        channel_id=0,
        name="v0",
        operator="scale_offset",
        inputs=("0",),
        params={},
    )
    runtime.on_connect(fake)
    sub1 = runtime.stream_sub(ChannelRef.virtual(0))
    sub2 = runtime.stream_sub(ChannelRef.virtual(0))
    assert sub1 is not None and sub2 is not None
    assert runtime.stream_unsub(sub1) is True
    # unrelated queue triggers scan-without-match path
    assert runtime.stream_unsub(queue.Queue()) is False
    assert runtime.stream_unsub(sub2) is True
    runtime.on_disconnect()


def test_fake_nxscope_stream_unsub_no_match_branch() -> None:
    fake = _FakeNxscope()
    fake.stream_unsub(queue.Queue())
