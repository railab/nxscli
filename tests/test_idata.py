import queue

import pytest  # type: ignore
from nxslib.dev import DeviceChannel

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
