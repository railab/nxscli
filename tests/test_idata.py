import queue

import pytest  # type: ignore
from nxslib.dev import DeviceChannel

from nxscli.idata import PluginData, PluginDataCb, PluginQueueData

g_queue: queue.Queue[list] = queue.Queue()


def dummy_stream_sub(ch):
    return g_queue


def dummy_stream_unsub(ch, q):
    assert ch == 0
    assert q == g_queue


def test_nxsclipdata_init():
    with pytest.raises(AssertionError):
        PluginData(None, None)

    channels = [DeviceChannel(0, 1, 2, "chan0")]
    with pytest.raises(AssertionError):
        PluginData(channels, None)

    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)

    gdata = PluginData(channels, cb)

    assert gdata.qdlist[0].queue is g_queue
    assert gdata.qdlist[0].chan == 0
    assert gdata.qdlist[0].is_numerical is False
    assert gdata.qdlist[0].vdim == 2
    assert gdata.qdlist[0].mlen == 0

    del gdata


def test_pluginqueuedata():
    q = queue.Queue()
    chan = DeviceChannel(0, 2, 2, "chan0")
    qdata = PluginQueueData(q, chan)

    assert isinstance(str(qdata), str)
    assert qdata.queue == q
    assert qdata.chan == chan.chan
    assert qdata.is_numerical == chan.is_numerical
    assert qdata.vdim == chan.vdim
    assert qdata.mlen == chan.mlen

    # no data on queue
    ret = qdata.queue_get(block=False)
    assert ret == []
    ret = qdata.queue_get(block=True, timeout=0.1)
    assert ret == []
