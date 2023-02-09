from nxscli.trigger import (
    DTriggerConfig,
    ETriggerType,
    TriggerHandler,
    trigger_from_str,
)


def test_triggerfromstr():
    x = trigger_from_str([("off", None)])
    assert x.ttype == ETriggerType.ALWAYS_OFF
    assert x.srcchan is None
    assert x.hoffset == 0
    assert x.level is None

    x = trigger_from_str([("on", None)])
    assert x.ttype == ETriggerType.ALWAYS_ON
    assert x.srcchan is None
    assert x.hoffset == 0
    assert x.level is None

    x = trigger_from_str([("er", None), "100", "10"])
    assert x.ttype == ETriggerType.EDGE_RISING
    assert x.hoffset == 100
    assert x.level == 10

    x = trigger_from_str([("ef", None), "200", "20"])
    assert x.ttype == ETriggerType.EDGE_FALLING
    assert x.srcchan is None
    assert x.hoffset == 200
    assert x.level == 20


def test_triggerhandle_alwaysoff():
    # always off
    dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    th = TriggerHandler(dtc)
    for _ in range(100):
        din = [(1,), (2,), (3,)]
        dout = th.data_triggered(din)
        assert dout == []


def test_triggerhandle_alwayson():
    # always on
    dtc = DTriggerConfig(ETriggerType.ALWAYS_ON)
    th = TriggerHandler(dtc)
    for _ in range(100):
        din = [(1,), (2,), (3,)]
        dout = th.data_triggered(din)
        assert dout == [(1,), (2,), (3,)]


def test_triggerhandle_edgerising1():
    # always on
    hoffset = 0
    level = 0
    dtc = DTriggerConfig(
        ETriggerType.EDGE_RISING, hoffset=hoffset, level=level
    )
    th = TriggerHandler(dtc)

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((-1,), ()), ((-2,), ()), ((-3,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((-3,), ()), ((-3,), ()), ((-3,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    # triggered - rising edge on 0
    din = [((0,), ()), ((1,), ()), ((2,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((1,), ()), ((2,), ())]

    din = [((3,), ()), ((4,), ()), ((5,), ())]
    dout = th.data_triggered(din)
    assert dout == [((3,), ()), ((4,), ()), ((5,), ())]

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((0,), ()), ((0,), ())]

    din = [((0,), ()), ((-1,), ()), ((-2,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((-1,), ()), ((-2,), ())]


def test_triggerhandle_edgerising2():
    # always on
    hoffset = 0
    level = 5
    dtc = DTriggerConfig(
        ETriggerType.EDGE_RISING, hoffset=hoffset, level=level
    )
    th = TriggerHandler(dtc)

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((-1,), ()), ((-2,), ()), ((-3,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((-4,), ()), ((-3,), ()), ((-2,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((1,), ()), ((2,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    # triggered
    din = [((4,), ()), ((5,), ()), ((6,), ()), ((7,), ())]
    dout = th.data_triggered(din)
    assert dout == [((5,), ()), ((6,), ()), ((7,), ())]

    din = [((3,), ()), ((4,), ()), ((5,), ())]
    dout = th.data_triggered(din)
    assert dout == [((3,), ()), ((4,), ()), ((5,), ())]

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((0,), ()), ((0,), ())]

    din = [((0,), ()), ((-1,), ()), ((-2,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((-1,), ()), ((-2,), ())]


def test_triggerhandle_edgefalling1():
    # always on
    hoffset = 0
    level = 0
    dtc = DTriggerConfig(
        ETriggerType.EDGE_FALLING, hoffset=hoffset, level=level
    )
    th = TriggerHandler(dtc)

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((1,), ()), ((2,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    # triggered
    din = [((2,), ()), ((1,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ())]

    din = [((-1,), ()), ((-2,), ()), ((-3,), ())]
    dout = th.data_triggered(din)
    assert dout == [((-1,), ()), ((-2,), ()), ((-3,), ())]

    din = [((2,), ()), ((1,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((2,), ()), ((1,), ()), ((0,), ())]

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((0,), ()), ((0,), ())]

    din = [((1,), ()), ((2,), ()), ((3,), ())]
    dout = th.data_triggered(din)
    assert dout == [((1,), ()), ((2,), ()), ((3,), ())]

    din = [((4,), ()), ((5,), ()), ((6,), ())]
    dout = th.data_triggered(din)
    assert dout == [((4,), ()), ((5,), ()), ((6,), ())]


def test_triggerhandle_edgefalling2():
    # always on
    hoffset = 0
    level = -5
    dtc = DTriggerConfig(
        ETriggerType.EDGE_FALLING, hoffset=hoffset, level=level
    )
    th = TriggerHandler(dtc)

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((0,), ()), ((1,), ()), ((2,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((3,), ()), ((2,), ()), ((1,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    din = [((-1,), ()), ((-2,), ()), ((-3,), ())]
    dout = th.data_triggered(din)
    assert dout == []

    # triggered
    din = [((-4,), ()), ((-5,), ()), ((-6,), ())]
    dout = th.data_triggered(din)
    assert dout == [((-5,), ()), ((-6,), ())]

    din = [((2,), ()), ((1,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((2,), ()), ((1,), ()), ((0,), ())]

    din = [((0,), ()), ((0,), ()), ((0,), ())]
    dout = th.data_triggered(din)
    assert dout == [((0,), ()), ((0,), ()), ((0,), ())]

    din = [((1,), ()), ((2,), ()), ((3,), ())]
    dout = th.data_triggered(din)
    assert dout == [((1,), ()), ((2,), ()), ((3,), ())]

    din = [((4,), ()), ((5,), ()), ((6,), ())]
    dout = th.data_triggered(din)
    assert dout == [((4,), ()), ((5,), ()), ((6,), ())]
