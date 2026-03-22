import queue

import numpy as np
import pytest  # type: ignore
from nxslib.dev import DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.channelref import ChannelRef
from nxscli.idata import PluginData, PluginDataCb, PluginQueueData
from nxscli.trigger import DTriggerConfig, ETriggerType, TriggerHandler

g_queue: queue.Queue[list] = queue.Queue()


def dummy_stream_sub(ch):
    return g_queue


def dummy_stream_unsub(q):
    assert q == g_queue


def test_pluginqueuedata():
    q = queue.Queue()
    chan = DeviceChannel(0, 2, 2, "chan0")
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)

    assert isinstance(str(qdata), str)
    assert qdata.queue == q
    assert qdata.chan == chan.data.chan
    assert qdata.is_numerical == chan.data.is_numerical
    assert qdata.vdim == chan.data.vdim
    assert qdata.mlen == chan.data.mlen

    # no data on queue
    ret = qdata.queue_get(block=False)
    assert ret == []
    ret = qdata.queue_get(block=True, timeout=0.1)
    assert ret == []

    TriggerHandler.cls_cleanup()


def test_pluginqueuedata_queue_get_returns_triggered_block_payload() -> None:
    class Block:
        def __init__(self) -> None:
            self.data = np.array([[1.0, 2.0], [3.0, 4.0]])
            self.meta = np.array([[10], [20]])

    q = queue.Queue()
    q.put([Block()])
    chan = DeviceChannel(0, 2, 2, "chan0")
    dtc = DTriggerConfig(ETriggerType.ALWAYS_ON)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)

    ret = qdata.queue_get(block=False)
    assert len(ret) == 1
    assert ret[0].data.shape == (2, 2)
    assert ret[0].meta.shape == (2, 1)
    TriggerHandler.cls_cleanup()


def test_pluginqueuedata_queue_get_handles_block_without_meta() -> None:
    class Block:
        def __init__(self) -> None:
            self.data = np.array([[1.0], [2.0]])
            self.meta = None

    q = queue.Queue()
    q.put([Block()])
    chan = DeviceChannel(0, 2, 1, "chan0")
    dtc = DTriggerConfig(ETriggerType.ALWAYS_ON)
    trig = TriggerHandler(0, dtc)
    qdata = PluginQueueData(q, chan, trig)

    ret = qdata.queue_get(block=False)
    assert len(ret) == 1
    assert ret[0].meta is None
    TriggerHandler.cls_cleanup()


def test_pluginqueuedata_exposes_trigger_event_metadata() -> None:
    q = queue.Queue()
    q.put(
        [
            DNxscopeStreamBlock(
                data=np.asarray([0.0, 0.0, 1.0, 2.0], dtype=float).reshape(
                    -1, 1
                ),
                meta=None,
            )
        ]
    )
    chan = DeviceChannel(7, 2, 1, "chan7")
    dtc = DTriggerConfig(ETriggerType.EDGE_RISING, hoffset=1, level=0.5)
    trig = TriggerHandler(7, dtc)
    qdata = PluginQueueData(q, chan, trig)

    ret = qdata.queue_get(block=False)
    event = qdata.pop_trigger_event()

    assert len(ret) == 1
    assert event is not None
    assert event.channel == 7
    assert event.sample_index == 1.0
    assert qdata.pop_trigger_event() is None
    TriggerHandler.cls_cleanup()


def test_nxsclipdata_init():
    channels = [DeviceChannel(0, 1, 2, "chan0")]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(0, dtc)]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)

    with pytest.raises(AssertionError):
        gdata = PluginData(channels, [], cb)

    gdata = PluginData(channels, trig, cb)

    assert gdata.qdlist[0].queue is g_queue
    assert gdata.qdlist[0].chan == 0
    assert gdata.qdlist[0].is_numerical is False
    assert gdata.qdlist[0].vdim == 2
    assert gdata.qdlist[0].mlen == 0

    TriggerHandler.cls_cleanup()


def test_nxsclipdata_queue_deinit_unsubscribes_all():
    unsubscribed: list[queue.Queue[list]] = []
    queues = [queue.Queue(), queue.Queue(), queue.Queue()]

    def stream_sub(channel: "ChannelRef"):  # noqa: ANN001
        return queues[channel.physical_id()]

    def stream_unsub(q):  # noqa: ANN001
        unsubscribed.append(q)

    channels = [
        DeviceChannel(0, 0, 1, "chan0"),
        DeviceChannel(1, 0, 1, "chan1"),
        DeviceChannel(2, 0, 1, "chan2"),
    ]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [
        TriggerHandler(0, dtc),
        TriggerHandler(1, dtc),
        TriggerHandler(2, dtc),
    ]
    cb = PluginDataCb(stream_sub, stream_unsub)
    pdata = PluginData(channels, trig, cb)

    assert len(pdata.qdlist) == 3
    pdata._queue_deinit()

    assert len(pdata.qdlist) == 0
    assert unsubscribed == queues
    TriggerHandler.cls_cleanup()


def test_nxsclipdata_virtual_channel_invalid_name_raises() -> None:
    channels = [DeviceChannel(-2, 0, 1, "virt_bad_name")]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(-2, dtc)]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)

    with pytest.raises(ValueError):
        _ = PluginData(channels, trig, cb)

    TriggerHandler.cls_cleanup()


def test_nxsclipdata_virtual_channel_name_is_supported() -> None:
    channels = [DeviceChannel(-2, 0, 1, "v2")]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(-2, dtc)]

    got = {"name": ""}

    def stream_sub(channel: "ChannelRef"):  # noqa: ANN001
        got["name"] = channel.virtual_name()
        return g_queue

    cb = PluginDataCb(stream_sub, dummy_stream_unsub)
    pdata = PluginData(channels, trig, cb)
    assert got["name"] == "v2"
    pdata._queue_deinit()

    TriggerHandler.cls_cleanup()


def test_nxsclipdata_drains_hidden_virtual_trigger_source() -> None:
    queues: dict[str, queue.Queue[list]] = {
        "0": queue.Queue(),
        "v0": queue.Queue(),
    }

    def stream_sub(channel: "ChannelRef"):  # noqa: ANN001
        if channel.is_virtual:
            return queues[channel.virtual_name()]
        return queues[str(channel.physical_id())]

    def stream_unsub(_q):  # noqa: ANN001
        return

    target = DeviceChannel(0, 2, 1, "chan0")
    _ = TriggerHandler(
        -2,
        DTriggerConfig(
            ETriggerType.ALWAYS_OFF,
            source_ref=ChannelRef.virtual(0),
        ),
    )
    trig = TriggerHandler(
        0,
        DTriggerConfig(
            ETriggerType.EDGE_RISING,
            srcchan=-2,
            level=0.5,
            source_ref=ChannelRef.virtual(0),
        ),
    )
    cb = PluginDataCb(stream_sub, stream_unsub)
    pdata = PluginData([target], [trig], cb)

    queues["v0"].put(
        [
            DNxscopeStreamBlock(
                data=np.asarray([0.0, 1.0, 1.0], dtype=float).reshape(-1, 1),
                meta=None,
            )
        ]
    )
    queues["0"].put(
        [
            DNxscopeStreamBlock(
                data=np.asarray([10.0, 11.0, 12.0], dtype=float).reshape(
                    -1, 1
                ),
                meta=None,
            )
        ]
    )

    ret = pdata.qdlist[0].queue_get(block=False)

    assert len(pdata._aux_qd) == 1
    assert len(ret) == 1
    assert ret[0].data.shape[0] > 0
    pdata._queue_deinit()
    TriggerHandler.cls_cleanup()


def test_nxsclipdata_missing_hidden_trigger_raises() -> None:
    def stream_sub(channel: "ChannelRef"):  # noqa: ANN001
        return queue.Queue()

    def stream_unsub(_q):  # noqa: ANN001
        return

    target = DeviceChannel(0, 2, 1, "chan0")
    trig = TriggerHandler(
        0,
        DTriggerConfig(
            ETriggerType.EDGE_RISING,
            srcchan=-2,
            level=0.5,
            source_ref=ChannelRef.virtual(0),
        ),
    )
    cb = PluginDataCb(stream_sub, stream_unsub)

    with pytest.raises(AssertionError):
        _ = PluginData([target], [trig], cb)

    stream_unsub(queue.Queue())
    TriggerHandler.cls_cleanup()


def test_nxsclipdata_find_trigger_prefers_visible_list() -> None:
    q = queue.Queue()
    chan = DeviceChannel(0, 2, 1, "chan0")
    trig = TriggerHandler(0, DTriggerConfig(ETriggerType.ALWAYS_ON))
    qdata = PluginData(
        [chan], [trig], PluginDataCb(lambda _ch: q, lambda _q: None)
    )

    assert qdata._find_trigger(0) is trig

    qdata._queue_deinit()
    TriggerHandler.cls_cleanup()
