from threading import Lock

import numpy as np
import pytest  # type: ignore
from nxslib.nxscope import DNxscopeStream, DNxscopeStreamBlock

from nxscli.trigger import (
    DTriggerConfig,
    DTriggerConfigReq,
    ETriggerCaptureMode,
    ETriggerType,
    TriggerHandler,
    trigger_from_req,
)

# we want to run TriggerHandler tests without concurency
global_lock = Lock()


def test_triggerfromstr():
    req = DTriggerConfigReq("off", None)
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.ALWAYS_OFF
    assert x.srcchan is None
    assert x.hoffset == 0
    assert x.level is None

    req = DTriggerConfigReq("on", None)
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.ALWAYS_ON
    assert x.srcchan is None
    assert x.hoffset == 0
    assert x.level is None

    req = DTriggerConfigReq("er", None, params=["100", "10"])
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.EDGE_RISING
    assert x.hoffset == 100
    assert x.level == 10

    req = DTriggerConfigReq("ef", None, params=["200", "20"])
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.EDGE_FALLING
    assert x.srcchan is None
    assert x.hoffset == 200
    assert x.level == 20

    req = DTriggerConfigReq("ef", 1, params=["200", "20"])
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.EDGE_FALLING
    assert x.srcchan == 1
    assert x.hoffset == 200
    assert x.level == 20

    req = DTriggerConfigReq("we", None, params=["12", "-0.5", "0.5"])
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.WINDOW_ENTER
    assert x.hoffset == 12
    assert x.window_low == -0.5
    assert x.window_high == 0.5

    req = DTriggerConfigReq("wx", None, params=["7", "-1.0", "1.0"])
    x = trigger_from_req(req)
    assert x.ttype == ETriggerType.WINDOW_EXIT
    assert x.hoffset == 7
    assert x.window_low == -1.0
    assert x.window_high == 1.0

    req = DTriggerConfigReq(
        "er",
        None,
        params=["5", "1.5"],
        mode="stop_after",
        pre_samples=3,
        post_samples=7,
        holdoff=2,
        rearm=True,
    )
    x = trigger_from_req(req)
    assert x.capture_mode is ETriggerCaptureMode.STOP_AFTER
    assert x.pre_samples == 3
    assert x.post_samples == 7
    assert x.holdoff == 2
    assert x.rearm is True
    assert x.effective_pre_samples == 3


# initialization logic
def test_triggerhandle_init():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        dtc0 = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th0 = TriggerHandler(0, dtc0)

        assert th0.chan == 0
        assert th0._src is None
        assert th0._cross == []
        assert len(th0._instances) == 1

        # we can register many trigger handlers for the same channel
        dtc0_1 = DTriggerConfig(ETriggerType.ALWAYS_ON)
        th0_1 = TriggerHandler(0, dtc0_1)

        assert th0_1.chan == 0
        assert th0_1._src is None
        assert th0_1._cross == []

        assert len(th0._instances) == 2
        assert len(th0_1._instances) == 2

        # no source channel registerd
        dtcx = DTriggerConfig(ETriggerType.ALWAYS_OFF, srcchan=2)
        thfail = TriggerHandler(1, dtcx)

        # one is waiting instnaces
        assert len(TriggerHandler._wait_for_src) == 1

        # try get data but we don't have required src channel
        with pytest.raises(AssertionError):
            din = [
                DNxscopeStream((0,), ()),
                DNxscopeStream((0,), ()),
                DNxscopeStream((0,), ()),
            ]
            _ = thfail.data_triggered(din)

        assert th0.chan == 0
        assert th0._src is None
        assert th0._cross == []

        assert len(th0._instances) == 3
        assert len(th0_1._instances) == 3

        # valid cross-channel source trigger
        dtc1 = DTriggerConfig(ETriggerType.ALWAYS_OFF, srcchan=0)
        th1 = TriggerHandler(1, dtc1)

        assert th0.chan == 0
        assert th0._src is None

        assert th0_1.chan == 0
        assert th0_1._src is None

        assert th1.chan == 1
        assert th1._src is not None
        assert th1 in th1._src._cross
        assert th1._cross == []

        assert len(th0._instances) == 4
        assert len(th0_1._instances) == 4
        assert len(th1._instances) == 4

        # another valid cross-channel source trigger
        dtc2 = DTriggerConfig(ETriggerType.ALWAYS_OFF, srcchan=0)
        th2 = TriggerHandler(2, dtc2)

        # another valid cross-channel source trigger
        dtc3 = DTriggerConfig(ETriggerType.ALWAYS_OFF, srcchan=0)
        th3 = TriggerHandler(3, dtc3)

        assert len(th0._instances) == 6
        assert len(th0_1._instances) == 6
        assert len(th1._instances) == 6
        assert len(th2._instances) == 6
        assert len(th3._instances) == 6

        assert th2._src is not None
        assert th2 in th2._src._cross

        assert th3._src is not None
        assert th3 in th3._src._cross

        # clean up
        TriggerHandler.cls_cleanup()


# check if clean up works
def test_triggerhandle_init2():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        dtc0 = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th0 = TriggerHandler(0, dtc0)

        # there should be no references to the previous test
        assert len(th0._instances) == 1

        # clean up
        TriggerHandler.cls_cleanup()


# cross trigger but no source channel during trigger registration
def test_triggerhandle_init3():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        dtc1 = DTriggerConfig(
            ETriggerType.EDGE_RISING, srcchan=0, hoffset=0, level=0
        )
        th1 = TriggerHandler(1, dtc1)

        assert th1.chan == 1
        assert th1._src is None  # no reference now
        assert th1._cross == []
        assert len(th1._instances) == 1

        # one is waiting instnaces
        assert len(TriggerHandler._wait_for_src) == 1

        # try get data but we don't have required src channel yet
        with pytest.raises(AssertionError):
            din = [
                DNxscopeStream((0,), ()),
                DNxscopeStream((0,), ()),
                DNxscopeStream((0,), ()),
            ]
            _ = th1.data_triggered(din)

        dtc0 = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th0 = TriggerHandler(0, dtc0)

        assert th0.chan == 0
        assert th0._src is None
        assert th1 in th0._cross
        assert len(th0._instances) == 2

        # no waiting instnaces
        assert len(TriggerHandler._wait_for_src) == 0

        # try get data, now should not fail
        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        _ = th1.data_triggered(din)

        # wait for source channel and celan up without registered source
        dtc3 = DTriggerConfig(
            ETriggerType.EDGE_RISING, srcchan=5, hoffset=0, level=0
        )
        th3 = TriggerHandler(3, dtc3)

        assert th3._src is None
        assert len(TriggerHandler._wait_for_src) == 1

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_alwaysoff():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # always off
        dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th = TriggerHandler(0, dtc)
        assert len(th._instances) == 1
        for _ in range(100):
            din = [
                DNxscopeStream((1,), ()),
                DNxscopeStream((2,), ()),
                DNxscopeStream((3,), ()),
            ]
            dout = th.data_triggered(din)
            assert dout == []

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_alwayson_does_not_emit_event():
    with global_lock:
        trig = TriggerHandler(0, DTriggerConfig(ETriggerType.ALWAYS_ON))
        data = [
            DNxscopeStreamBlock(
                data=np.array([[1.0], [2.0], [3.0]]),
                meta=np.array([[0], [0], [0]]),
            )
        ]

        ret = trig.data_triggered(data)

        assert ret == data
        assert trig.pop_trigger_event() is None

        TriggerHandler.cls_cleanup()


def test_triggerhandle_alwayson():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # always on
        dtc = DTriggerConfig(ETriggerType.ALWAYS_ON)
        th = TriggerHandler(0, dtc)
        assert len(th._instances) == 1
        for _ in range(100):
            din = [
                DNxscopeStream((1,), ()),
                DNxscopeStream((2,), ()),
                DNxscopeStream((3,), ()),
            ]
            dout = th.data_triggered(din)
            assert dout == [
                DNxscopeStream((1,), ()),
                DNxscopeStream((2,), ()),
                DNxscopeStream((3,), ()),
            ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_edgerising1():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # rising edge on 0
        hoffset = 0
        level = 0
        dtc = DTriggerConfig(
            ETriggerType.EDGE_RISING, hoffset=hoffset, level=level
        )
        th = TriggerHandler(0, dtc)

        assert len(th._instances) == 1

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
            DNxscopeStream((-3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((-3,), ()),
            DNxscopeStream((-3,), ()),
            DNxscopeStream((-3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        # triggered - rising edge on 0
        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]

        din = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_edgerising2():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # rising edge on 5
        hoffset = 0
        level = 5
        dtc = DTriggerConfig(
            ETriggerType.EDGE_RISING, hoffset=hoffset, level=level
        )
        th = TriggerHandler(0, dtc)

        assert len(th._instances) == 1

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
            DNxscopeStream((-3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((-4,), ()),
            DNxscopeStream((-3,), ()),
            DNxscopeStream((-2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        # triggered
        din = [
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
            DNxscopeStream((6,), ()),
            DNxscopeStream((7,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((6,), ()),
            DNxscopeStream((7,), ()),
        ]

        din = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_edgefalling1():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # falling edge on 0
        hoffset = 0
        level = 0
        dtc = DTriggerConfig(
            ETriggerType.EDGE_FALLING, hoffset=hoffset, level=level
        )
        th = TriggerHandler(0, dtc)

        assert len(th._instances) == 1

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        # triggered
        din = [
            DNxscopeStream((2,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [DNxscopeStream((-1,), ())]

        din = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
            DNxscopeStream((-3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
            DNxscopeStream((-3,), ()),
        ]

        din = [
            DNxscopeStream((2,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((2,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
            DNxscopeStream((3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
            DNxscopeStream((3,), ()),
        ]

        din = [
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
            DNxscopeStream((6,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
            DNxscopeStream((6,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_edgefalling2():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # falling edge on -5
        hoffset = 0
        level = -5
        dtc = DTriggerConfig(
            ETriggerType.EDGE_FALLING, hoffset=hoffset, level=level
        )
        th = TriggerHandler(0, dtc)

        assert len(th._instances) == 1

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((2,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        din = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-2,), ()),
            DNxscopeStream((-3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == []

        # triggered
        din = [
            DNxscopeStream((-4,), ()),
            DNxscopeStream((-5,), ()),
            DNxscopeStream((-6,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [DNxscopeStream((-6,), ())]

        din = [
            DNxscopeStream((2,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((2,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]

        din = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
            DNxscopeStream((3,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
            DNxscopeStream((3,), ()),
        ]

        din = [
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
            DNxscopeStream((6,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
            DNxscopeStream((6,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_windowenter() -> None:
    with global_lock:
        dtc = DTriggerConfig(
            ETriggerType.WINDOW_ENTER,
            hoffset=0,
            window_low=-0.5,
            window_high=0.5,
        )
        th = TriggerHandler(0, dtc)

        din = [
            DNxscopeStream((-1.0,), ()),
            DNxscopeStream((-0.8,), ()),
            DNxscopeStream((-0.6,), ()),
        ]
        assert th.data_triggered(din) == []

        din = [
            DNxscopeStream((-0.4,), ()),
            DNxscopeStream((0.0,), ()),
            DNxscopeStream((0.4,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == din

        TriggerHandler.cls_cleanup()


def test_triggerhandle_windowexit() -> None:
    with global_lock:
        dtc = DTriggerConfig(
            ETriggerType.WINDOW_EXIT,
            hoffset=0,
            window_low=-0.5,
            window_high=0.5,
        )
        th = TriggerHandler(0, dtc)

        din = [
            DNxscopeStream((-0.2,), ()),
            DNxscopeStream((0.0,), ()),
            DNxscopeStream((0.2,), ()),
        ]
        assert th.data_triggered(din) == []

        din = [
            DNxscopeStream((0.4,), ()),
            DNxscopeStream((0.6,), ()),
            DNxscopeStream((0.8,), ()),
        ]
        dout = th.data_triggered(din)
        assert dout == [
            DNxscopeStream((0.6,), ()),
            DNxscopeStream((0.8,), ()),
        ]

        TriggerHandler.cls_cleanup()


def test_triggerhandle_window_helpers_short_input() -> None:
    with global_lock:
        dtc = DTriggerConfig(
            ETriggerType.WINDOW_ENTER,
            hoffset=0,
            window_low=-0.5,
            window_high=0.5,
        )
        th = TriggerHandler(0, dtc)

        assert th._windowenter([], 0, -0.5, 0.5).state is False
        assert (
            th._windowenter([DNxscopeStream((0.0,), ())], 0, -0.5, 0.5).state
            is False
        )
        assert th._windowexit([], 0, -0.5, 0.5).state is False
        assert (
            th._windowexit([DNxscopeStream((0.0,), ())], 0, -0.5, 0.5).state
            is False
        )

        TriggerHandler.cls_cleanup()


def test_triggerhandle_chanxtochany_nohoffset():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # chan0 - always off
        dtc0 = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th0 = TriggerHandler(0, dtc0)

        # chan1 - trigger on chan0 rising endge 4
        hoffset = 0
        level = 4
        srcchan = 0
        dtc1 = DTriggerConfig(
            ETriggerType.EDGE_RISING,
            srcchan=srcchan,
            hoffset=hoffset,
            level=level,
        )
        th1 = TriggerHandler(1, dtc1)

        assert len(th0._instances) == 2
        assert len(th1._instances) == 2

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        din0 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((4,), ()),
            DNxscopeStream((3,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        # th1 triggered from now - but th0 is always off
        din0 = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((10,), ()),
            DNxscopeStream((11,), ()),
            DNxscopeStream((12,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []  # no data yet

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]

        # th1 is now triggered

        din1 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]

        din1 = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandle_chanxtochany_hoffset():
    with global_lock:
        assert len(TriggerHandler._instances) == 0
        assert len(TriggerHandler._wait_for_src) == 0

        # chan0 - always off
        dtc0 = DTriggerConfig(ETriggerType.ALWAYS_OFF)
        th0 = TriggerHandler(0, dtc0)

        # chan1 - trigger on chan0 rising endge 4
        hoffset = 2
        level = 4
        srcchan = 0
        dtc1 = DTriggerConfig(
            ETriggerType.EDGE_RISING,
            srcchan=srcchan,
            hoffset=hoffset,
            level=level,
        )
        th1 = TriggerHandler(1, dtc1)

        assert len(th0._instances) == 2
        assert len(th1._instances) == 2

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        din0 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((-1,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((4,), ()),
            DNxscopeStream((3,), ()),
            DNxscopeStream((2,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []

        # th1 triggerd with hoffset - but th0 is always off
        din0 = [
            DNxscopeStream((3,), ()),
            DNxscopeStream((4,), ()),
            DNxscopeStream((5,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((10,), ()),
            DNxscopeStream((11,), ()),
            DNxscopeStream((12,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == []  # no data yet

        din0 = [
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
            DNxscopeStream((0,), ()),
        ]
        dout0 = th0.data_triggered(din0)
        assert dout0 == []

        din1 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]

        # th1 is now triggered
        din1 = [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
            DNxscopeStream((1,), ()),
        ]

        din1 = [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
        ]
        dout1 = th1.data_triggered(din1)
        assert dout1 == [
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
            DNxscopeStream((-1,), ()),
        ]

        # clean up
        TriggerHandler.cls_cleanup()


def test_triggerhandler_block_helpers_and_cache_paths() -> None:
    with global_lock:
        dtc = DTriggerConfig(ETriggerType.EDGE_RISING, hoffset=2, level=5.0)
        th = TriggerHandler(0, dtc)

        assert th._combined_vector([], 0) == []
        assert th._edgerising([], 0, 0.0).state is False
        assert th._edgefalling([], 0, 0.0).state is False
        assert th._slice_from([], 1) == []
        assert th._sample_count([DNxscopeStream((1,), ())]) == 1
        assert th._slice_range([], 0, 0) == []
        assert th._slice_range([], 0, 1) == []
        assert th._slice_range([DNxscopeStream((1,), ())], 0, 1) == [
            DNxscopeStream((1,), ())
        ]
        assert th._tail_samples([DNxscopeStream((1,), ())], 0) == []

        block = DNxscopeStreamBlock(data=np.array([[0.0], [2.0]]), meta=None)
        out = th.data_triggered([block])
        assert out == []
        assert th._cache

        sliced = th._slice_from([block], 1)
        assert len(sliced) == 1
        assert sliced[0].data.shape[0] == 1
        assert sliced[0].meta is None

        tail = th._cache_tail([block], 1)
        assert len(tail) == 1
        assert tail[0].data.shape[0] == 1

        assert th._cache_tail([block], 0) == [block]
        assert th._cache_tail([], 1) == []
        assert th._cache_tail([DNxscopeStream((1,), ())], 1) == [
            DNxscopeStream((1,), ())
        ]

        block0 = DNxscopeStreamBlock(data=np.array([[0.0], [1.0]]), meta=None)
        block1 = DNxscopeStreamBlock(data=np.array([[2.0]]), meta=None)
        assert th._slice_from([block0, block1], 2) == [block1]

        scalar_block = DNxscopeStreamBlock(data=np.array([[7.0]]), meta=None)
        assert th._combined_vector([scalar_block], 0) == [7.0]

        list_block = DNxscopeStreamBlock(
            data=np.array([[1.0], [2.0]]), meta=None
        )
        assert th._combined_vector([list_block], 0) == [1.0, 2.0]

        concat0 = DNxscopeStreamBlock(data=np.array([[0.0]]), meta=None)
        concat1 = DNxscopeStreamBlock(data=np.array([[1.0]]), meta=None)
        assert th._combined_vector([concat0, concat1], 0) == [0.0, 1.0]
        sliced_range = th._slice_range([concat0, concat1], 0, 5)
        assert len(sliced_range) == 2

        TriggerHandler.cls_cleanup()


def test_triggerhandler_block_cache_hoffset_zero_keeps_current_batch() -> None:
    with global_lock:
        dtc = DTriggerConfig(ETriggerType.EDGE_RISING, hoffset=0, level=5.0)
        th = TriggerHandler(0, dtc)
        block = DNxscopeStreamBlock(data=np.array([[0.0], [2.0]]), meta=None)
        payload = [block]

        out = th.data_triggered(payload)

        assert out == []
        assert th._cache is payload
        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_block_current_batch() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.EDGE_RISING,
                level=0.5,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=1,
            ),
        )

        block = DNxscopeStreamBlock(
            data=np.array([[0.0], [0.0], [1.0], [2.0]]),
            meta=np.array([[0], [1], [2], [3]]),
        )
        out = trig.data_triggered([block])

        assert len(out) == 1
        assert out[0].data.tolist() == [[0.0], [0.0], [1.0], [2.0]]
        assert out[0].meta.tolist() == [[0], [1], [2], [3]]

        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_block_boundary() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.EDGE_RISING,
                level=0.5,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=2,
            ),
        )

        first = DNxscopeStreamBlock(
            data=np.array([[0.0], [0.0]]),
            meta=np.array([[0], [1]]),
        )
        second = DNxscopeStreamBlock(
            data=np.array([[1.0], [2.0], [3.0]]),
            meta=np.array([[2], [3], [4]]),
        )
        third = DNxscopeStreamBlock(
            data=np.array([[4.0], [5.0]]),
            meta=np.array([[5], [6]]),
        )

        out1 = trig.data_triggered([first])
        out2 = trig.data_triggered([second])
        out3 = trig.data_triggered([third])

        assert out1[0].data.tolist() == [[0.0], [0.0]]
        assert out2[0].data.tolist() == [[1.0], [2.0], [3.0]]
        assert out3 == []

        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_block_carries_post_tail() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.EDGE_RISING,
                level=0.5,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=3,
            ),
        )

        assert trig.data_triggered([]) == []

        first = DNxscopeStreamBlock(
            data=np.array([[0.0]]),
            meta=np.array([[0]]),
        )
        second = DNxscopeStreamBlock(
            data=np.array([[1.0]]),
            meta=np.array([[1]]),
        )
        third = DNxscopeStreamBlock(
            data=np.array([[2.0], [3.0], [4.0]]),
            meta=np.array([[2], [3], [4]]),
        )

        out1 = trig.data_triggered([first])
        out2 = trig.data_triggered([second])
        out3 = trig.data_triggered([third])
        out4 = trig.data_triggered([third])

        assert out1[0].data.tolist() == [[0.0]]
        assert out2[0].data.tolist() == [[1.0]]
        assert out3[0].data.tolist() == [[2.0], [3.0], [4.0]]
        assert out4 == []

        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_block_boundary_zero_post() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.EDGE_RISING,
                level=0.5,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=0,
            ),
        )

        first = DNxscopeStreamBlock(
            data=np.array([[0.0]]),
            meta=np.array([[0]]),
        )
        second = DNxscopeStreamBlock(
            data=np.array([[1.0]]),
            meta=np.array([[1]]),
        )

        out1 = trig.data_triggered([first])
        out2 = trig.data_triggered([second])

        assert out1[0].data.tolist() == [[0.0]]
        assert out2[0].data.tolist() == [[1.0]]

        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_legacy_payload_unsupported() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.EDGE_RISING,
                level=0.5,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=1,
            ),
        )

        with pytest.raises(NotImplementedError):
            trig.data_triggered(
                [
                    DNxscopeStream((0.0,), ()),
                    DNxscopeStream((1.0,), ()),
                ]
            )

        TriggerHandler.cls_cleanup()


def test_triggerhandle_stop_after_alwayson_does_not_emit_event() -> None:
    with global_lock:
        trig = TriggerHandler(
            0,
            DTriggerConfig(
                ETriggerType.ALWAYS_ON,
                capture_mode=ETriggerCaptureMode.STOP_AFTER,
                post_samples=2,
            ),
        )
        data = [
            DNxscopeStreamBlock(
                data=np.array([[1.0], [2.0], [3.0]]),
                meta=np.array([[0], [0], [0]]),
            )
        ]

        ret = trig.data_triggered(data)

        assert len(ret) == 1
        assert np.array_equal(ret[0].data, np.array([[1.0], [2.0], [3.0]]))
        assert trig.pop_trigger_event() is None

        TriggerHandler.cls_cleanup()


def test_triggerhandle_emits_event_metadata() -> None:
    with global_lock:
        trig = TriggerHandler(
            7,
            DTriggerConfig(ETriggerType.EDGE_RISING, hoffset=2, level=0.5),
        )
        block = DNxscopeStreamBlock(
            data=np.array([[0.0], [0.0], [1.0], [2.0]]),
            meta=None,
        )

        out = trig.data_triggered([block])
        event = trig.pop_trigger_event()

        assert len(out) == 1
        assert event is not None
        assert event.channel == 7
        assert event.sample_index == 2.0
        assert trig.pop_trigger_event() is None

        TriggerHandler.cls_cleanup()


def test_triggerhandle_start_after_emits_event_only_once() -> None:
    with global_lock:
        trig = TriggerHandler(
            7,
            DTriggerConfig(ETriggerType.EDGE_RISING, hoffset=2, level=0.5),
        )
        first = DNxscopeStreamBlock(
            data=np.array([[0.0], [0.0], [1.0], [2.0]]),
            meta=None,
        )
        second = DNxscopeStreamBlock(
            data=np.array([[3.0], [4.0], [5.0]]),
            meta=None,
        )

        trig.data_triggered([first])
        event1 = trig.pop_trigger_event()

        trig.data_triggered([second])
        event2 = trig.pop_trigger_event()

        assert event1 is not None
        assert event1.sample_index == 2.0
        assert event2 is None

        TriggerHandler.cls_cleanup()


def test_triggerhandle_edgerising_hoffset():
    # TODO
    pass


def test_triggerhandle_chanxtochanx():
    pass


def test_triggerhandle_allthesame():
    pass
