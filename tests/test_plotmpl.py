import queue

import pytest  # type: ignore
from matplotlib.axes import Axes  # type: ignore
from matplotlib.figure import Figure  # type: ignore
from nxslib.dev import DeviceChannel

from nxscli.idata import PluginDataCb, PluginQueueData
from nxscli.plot_mpl import (
    PlotDataAxesMpl,
    PlotDataCommon,
    PluginAnimationCommonMpl,
    PluginPlotMpl,
)
from nxscli.trigger import DTriggerConfig, ETriggerType, TriggerHandler


def test_plotdatacommon():
    chan = DeviceChannel(0, 1, 2, "chan0")
    x = PlotDataCommon(chan)

    assert x.samples_max == 0
    x.samples_max = 100
    assert x.samples_max == 100

    assert x.xdata == [[], []]
    assert x.ydata == [[], []]

    x.xdata_extend([[1, 2], [3, 4]])
    x.ydata_extend([[5, 6], [7, 8]])
    assert x.xdata == [[1, 2], [3, 4]]
    assert x.ydata == [[5, 6], [7, 8]]
    x.xdata_extend([[9], [10]])
    x.ydata_extend([[11], [12]])
    assert x.xdata == [[1, 2, 9], [3, 4, 10]]
    assert x.ydata == [[5, 6, 11], [7, 8, 12]]

    x.samples_max = 5
    x.xdata_extend_max([[13, 14], [16, 17]])
    x.ydata_extend_max([[19, 20], [22, 23]])
    x.xdata_extend_max([[15], [18]])
    x.ydata_extend_max([[21], [24]])

    assert x.xdata == [[2, 9, 13, 14, 15], [4, 10, 16, 17, 18]]
    assert x.ydata == [[6, 11, 19, 20, 21], [8, 12, 22, 23, 24]]
    x.xdata_extend_max([[25], [26]])
    x.ydata_extend_max([[27], [28]])
    assert x.xdata == [[9, 13, 14, 15, 25], [10, 16, 17, 18, 26]]
    assert x.ydata == [[11, 19, 20, 21, 27], [12, 22, 23, 24, 28]]


def test_plotdataaxesmpl():
    fig = Figure()
    axes = Axes(fig, (1, 1, 2, 6))

    # not numerical channels
    chan = DeviceChannel(0, 1, 2, "chan0")
    with pytest.raises(TypeError):
        x = PlotDataAxesMpl(axes, chan)

    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    x = PlotDataAxesMpl(axes, chan)

    assert x.ax is axes
    assert str(x) is not None

    x.set_xlim((0, 1))
    assert x.xlim == (0, 1)
    x.set_ylim((2, 3))
    assert x.ylim == (2, 3)

    x.plot_title = "test"
    assert x.plot_title == "test"

    x.plot()
    x.xaxis_disable()
    x.xaxis_set_ticks([])

    x = PlotDataAxesMpl(axes, chan, fmt=None)
    assert x._fmt == ["", ""]

    x = PlotDataAxesMpl(axes, chan, fmt=["o", "b"])
    assert x._fmt == ["o", "b"]


def test_pluginanimationcommonmpl():
    q = queue.Queue()
    chan = DeviceChannel(chan=0, _type=2, vdim=2, name="chan0")
    fig = Figure()
    axes = Axes(fig, (1, 1, 2, 6))
    pdata = PlotDataAxesMpl(axes, chan)
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    qdata = PluginQueueData(q, chan, dtc)
    x = PluginAnimationCommonMpl(fig, pdata, qdata, False)

    x.stop()
    # TODO


def dummy_stream_sub(ch):
    pass


def dummy_stream_unsub(q):
    pass


def test_pluginplotmpl():
    chanlist = [
        DeviceChannel(chan=0, _type=1, vdim=2, name="chan0"),  # not numerical
        DeviceChannel(chan=1, _type=2, vdim=1, name="chan1"),
        DeviceChannel(chan=2, _type=2, vdim=2, name="chan2"),
    ]
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    trig = [TriggerHandler(1, dtc), TriggerHandler(2, dtc)]
    cb = PluginDataCb(dummy_stream_sub, dummy_stream_unsub)
    x = PluginPlotMpl(chanlist, trig, cb)

    assert x.fig is not None
    assert x.ani == []
    assert len(x.plist) > 0
    assert len(x._chanlist) == 2  # one channel not numerical
    assert x._fmt == [None, None]

    # test fmt configuration
    x = PluginPlotMpl(chanlist, trig, cb, fmt="o")
    assert x._fmt == [["o"], ["o", "o"]]

    x = PluginPlotMpl(chanlist, trig, cb, fmt=[["o"], ["b", "b"]])
    assert x._fmt == [["o"], ["b", "b"]]

    # invalid vector fmt for chan 2
    with pytest.raises(AssertionError):
        x = PluginPlotMpl(chanlist, trig, cb, fmt=["o", "b"])
    # invalid channels fmt
    with pytest.raises(AssertionError):
        x = PluginPlotMpl(chanlist, trig, cb, fmt=["o", "b", "c"])

    # TODO

    TriggerHandler.cls_cleanup()
