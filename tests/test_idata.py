import queue
from typing import TYPE_CHECKING

import pytest  # type: ignore
from nxslib.dev import DeviceChannel

from nxscli.idata import PluginData, PluginDataCb, PluginQueueData
from nxscli.trigger import DTriggerConfig, ETriggerType, TriggerHandler

if TYPE_CHECKING:
    from nxscli.channelref import ChannelRef

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
