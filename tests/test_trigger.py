from threading import Lock

import pytest  # type: ignore
from nxslib.nxscope import DNxscopeStream

from nxscli.trigger import (
    DTriggerConfig,
    DTriggerConfigReq,
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
            DNxscopeStream((0,), ()),
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
            DNxscopeStream((5,), ()),
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
        assert dout == [DNxscopeStream((0,), ()), DNxscopeStream((-1,), ())]

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
        assert dout == [DNxscopeStream((-5,), ()), DNxscopeStream((-6,), ())]

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


def test_triggerhandle_edgerising_hoffset():
    # TODO
    pass


def test_triggerhandle_chanxtochanx():
    pass


def test_triggerhandle_allthesame():
    pass
