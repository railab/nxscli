import queue
from types import SimpleNamespace

import numpy as np
from nxslib.dev import DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.channelref import ChannelRef
from nxscli.stream_hub import SharedStreamProvider


class _FakeNxscopeHub:
    def __init__(self) -> None:
        self._channels = {
            0: DeviceChannel(0, 10, 1, "ch0"),
            1: DeviceChannel(1, 10, 1, "ch1"),
        }
        self.dev = SimpleNamespace(data=SimpleNamespace(chmax=2))
        self.sub_calls: dict[int, int] = {}
        self.unsub_calls = 0
        self.source_queues: dict[int, queue.Queue] = {}

    def dev_channel_get(self, chid: int):
        return self._channels.get(chid)

    def stream_sub(self, chid: int):
        self.sub_calls[chid] = self.sub_calls.get(chid, 0) + 1
        q = queue.Queue()
        self.source_queues[chid] = q
        return q

    def stream_unsub(self, subq) -> None:
        self.unsub_calls += 1
        for chid in list(self.source_queues.keys()):
            if self.source_queues[chid] is subq:
                del self.source_queues[chid]
                return


def _block(value: float) -> DNxscopeStreamBlock:
    return DNxscopeStreamBlock(
        data=np.asarray([[value]], dtype=np.float64),
        meta=None,
    )


def test_stream_hub_fanout_single_upstream_subscription() -> None:
    hub = SharedStreamProvider()
    fake = _FakeNxscopeHub()
    hub.on_connect(fake)

    sub1 = hub.stream_sub(ChannelRef.physical(0))
    sub2 = hub.stream_sub(ChannelRef.physical(0))
    assert sub1 is not None
    assert sub2 is not None

    hub.on_stream_start()
    assert fake.sub_calls[0] == 1

    fake.source_queues[0].put([_block(1.0)])
    hub._thread_common()
    out1 = sub1.get(block=True, timeout=0.2)
    out2 = sub2.get(block=True, timeout=0.2)
    assert float(out1[0].data[0, 0]) == 1.0
    assert float(out2[0].data[0, 0]) == 1.0

    assert hub.stream_unsub(sub1) is True
    assert hub.stream_unsub(sub2) is True
    assert fake.unsub_calls >= 1
    hub.on_stream_stop()
    hub.on_disconnect()


def test_stream_hub_subscribe_after_start_and_stop_paths() -> None:
    hub = SharedStreamProvider()
    fake = _FakeNxscopeHub()

    hub.on_stream_start()  # no nxscope
    hub._thread_common()  # not started

    hub.on_connect(fake)
    hub.on_stream_start()  # no subscribers
    hub._thread_common()  # started but no sources

    sub = hub.stream_sub(ChannelRef.physical(1))
    assert sub is not None
    assert fake.sub_calls[1] == 1

    # empty source queue path
    hub._thread_common()

    # empty blocks path
    fake.source_queues[1].put([])
    hub._thread_common()

    assert hub.stream_unsub(queue.Queue()) is False
    assert hub.stream_unsub(sub) is True
    hub.on_stream_stop()
    hub.on_stream_stop()  # already stopped


def test_stream_hub_nonphysical_and_channel_paths() -> None:
    hub = SharedStreamProvider()
    fake = _FakeNxscopeHub()

    assert hub.channel_get(ChannelRef.physical(0)) is None
    assert hub.stream_sub(ChannelRef.virtual(9)) is None
    assert hub.channel_list() == ()

    hub.on_connect(fake)
    assert hub.channel_get(ChannelRef.virtual(0)) is None
    ch0 = hub.channel_get(ChannelRef.physical(0))
    assert ch0 is not None
    assert ch0.data.chan == 0

    hub.on_disconnect()
    assert hub.stream_unsub(queue.Queue()) is False


def test_stream_hub_connect_disconnect_reset() -> None:
    hub = SharedStreamProvider()
    fake = _FakeNxscopeHub()
    hub.on_connect(fake)
    sub = hub.stream_sub(ChannelRef.physical(0))
    assert sub is not None
    hub.on_stream_start()
    hub.on_stream_start()  # already started
    hub.on_disconnect()
    # disconnected provider should not find previous subscription
    assert hub.stream_unsub(sub) is False


def test_stream_hub_internal_branch_paths() -> None:
    hub = SharedStreamProvider()
    fake = _FakeNxscopeHub()

    # _ensure_source_sub_locked with no nxscope
    hub._ensure_source_sub_locked(0)

    hub.on_connect(fake)
    hub._ensure_source_sub_locked(0)
    # repeated ensure must not resubscribe same channel
    hub._ensure_source_sub_locked(0)
    assert fake.sub_calls[0] == 1

    # mapped queue missing from subscriber list
    sub = hub.stream_sub(ChannelRef.physical(0))
    assert sub is not None
    hub._subscribers[0].clear()
    assert hub.stream_unsub(sub) is True

    # started with no nxscope path in stop
    hub._started = True
    hub._nxscope = None
    hub._source_subs = {0: queue.Queue()}
    hub.on_stream_stop()


def test_fake_nxscopehub_stream_unsub_paths() -> None:
    fake = _FakeNxscopeHub()
    q0 = fake.stream_sub(0)
    fake.stream_unsub(queue.Queue())
    assert 0 in fake.source_queues
    fake.stream_unsub(q0)
    assert 0 not in fake.source_queues
