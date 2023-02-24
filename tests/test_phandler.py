import pytest  # type: ignore
from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.iplugin import (
    DPluginDescription,
    EPluginType,
    IPlugin,
    IPluginPlotDynamic,
    IPluginPlotStatic,
    IPluginText,
)
from nxscli.phandler import PluginHandler
from nxscli.trigger import DTriggerConfigReq


class MockPlugin1(IPlugin):
    def __init__(self):
        super().__init__(EPluginType.TEXT)
        self._wait_for = False

    @property
    def stream(self) -> bool:
        return False

    def wait_for_plugin(self) -> bool:
        ret = self._wait_for
        self._wait_for = True
        return ret

    def stop(self) -> None:
        pass

    def data_wait(self, timeout=None) -> bool:
        return True

    def start(self, kwargs) -> bool:
        return True

    def result(self):
        return "1"


class MockPlugin2(IPluginText):
    def __init__(self):
        super().__init__()

    @property
    def stream(self) -> bool:
        return True

    def stop(self) -> None:
        pass

    def data_wait(self, timeout=None) -> bool:
        return True

    def start(self, kwargs) -> bool:
        return True

    def result(self):
        return "2"


class MockPlugin3(IPluginPlotDynamic):
    def __init__(self):
        super().__init__()

    @property
    def stream(self) -> bool:
        return True

    def stop(self) -> None:
        pass

    def data_wait(self, timeout=None) -> bool:
        return True

    def start(self, kwargs) -> bool:
        return True

    def result(self):
        return None


class MockPlugin4(IPluginPlotStatic):
    def __init__(self):
        super().__init__()

    @property
    def stream(self) -> bool:
        return True

    def stop(self) -> None:
        pass

    def data_wait(self, timeout=None) -> bool:
        return False

    def start(self, kwargs) -> bool:
        return True

    def result(self):  # pragma: no cover
        return None


def test_phandler_init():
    # no plugins at the beginning
    p = PluginHandler([])
    assert isinstance(p, PluginHandler)
    assert p.names == []
    p.cleanup()

    # valid data
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    p = PluginHandler(plugins=plugins)
    assert isinstance(p, PluginHandler)
    assert p.names == ["plugin1", "plugin2"]
    assert p.plugin_get("plugin1") == MockPlugin1
    assert p.plugin_get("plugin2") == MockPlugin2
    assert p.names == ["plugin1", "plugin2"]

    # add plugin = valid data
    p.plugin_add(("plugin3", MockPlugin3))
    assert p.names == ["plugin1", "plugin2", "plugin3"]

    # plugins instances
    assert isinstance(p.plugins["plugin1"](), MockPlugin1)
    assert isinstance(p.plugins["plugin2"](), MockPlugin2)
    assert isinstance(p.plugins["plugin3"](), MockPlugin3)

    # clean up
    p.cleanup()


@pytest.fixture
def nxscope():
    intf = DummyDev()
    parse = Parser()
    nxscope = NxscopeHandler(intf, parse)
    return nxscope


def test_phandler_connect(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    p = PluginHandler(plugins=plugins)

    # nxs not connected
    with pytest.raises(AssertionError):
        _ = p.dev
    with pytest.raises(AssertionError):
        _ = p.stream_start()
    with pytest.raises(AssertionError):
        _ = p.stream_stop()
    with pytest.raises(AssertionError):
        _ = p.channels_configure([])

    # connect nxslib instance
    p.nxscope_connect(nxscope)

    # nxscope should be connected
    assert p.dev is not None

    # chanlist
    p.channels_configure([])
    p.channels_configure([-1], 1)
    p.channels_configure([1, 2], [1, 2], writenow=True)

    # clean up
    p.cleanup()


def test_phandler_enable():
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    p = PluginHandler(plugins=plugins)

    # no plugins enabled at default
    assert len(p.enabled) == 0

    pid1 = p.enable("plugin2", **{})
    assert len(p.enabled) == 1
    assert pid1 == 0
    assert p.enabled[0][0] == 0
    assert p.enabled[0][1] == MockPlugin2
    assert p.enabled[0][2] == {}

    pid2 = p.enable("plugin1", **{"arg1": 1})
    assert len(p.enabled) == 2
    assert pid2 == 1
    assert p.enabled[0][0] == 0
    assert p.enabled[0][1] == MockPlugin2
    assert p.enabled[0][2] == {}

    assert p.enabled[0][2] == {}
    assert p.enabled[1][0] == 1
    assert p.enabled[1][1] == MockPlugin1
    assert p.enabled[1][2]["arg1"] == 1

    # we can enable plugins multiple times
    pid3 = p.enable("plugin1", **{"arg1": "test"})
    assert len(p.enabled) == 3
    assert pid3 == 2
    assert p.enabled[0][0] == 0
    assert p.enabled[0][1] == MockPlugin2
    assert p.enabled[0][2] == {}

    assert p.enabled[1][0] == 1
    assert p.enabled[1][1] == MockPlugin1
    assert p.enabled[1][2]["arg1"] == 1

    assert p.enabled[2][0] == 2
    assert p.enabled[2][1] == MockPlugin1
    assert p.enabled[2][2]["arg1"] == "test"

    # disable plugin1
    p.disable(pid1)
    assert len(p.enabled) == 2
    assert p.enabled[0][0] == 1
    assert p.enabled[1][0] == 2

    # once again disable plugin1
    with pytest.raises(AttributeError):
        p.disable(pid1)

    # disable plugin2
    p.disable(pid2)
    assert len(p.enabled) == 1
    assert p.enabled[0][0] == 2

    # once again disable plugin2
    with pytest.raises(AttributeError):
        p.disable(pid2)

    # disable plugin3
    p.disable(pid3)
    assert len(p.enabled) == 0

    # once again disable plugin3
    with pytest.raises(AttributeError):
        p.disable(pid3)

    # clean up
    p.cleanup()


def test_phandler_start_ready(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
        DPluginDescription("plugin3", MockPlugin3),
    ]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # enable all plugins
    p.enable("plugin1", **{})
    p.enable("plugin2", **{})
    p.enable("plugin3", **{})
    assert len(p.enabled) == 3

    # start plugins
    p.start()

    ret = p.ready()
    assert ret[0].result() == "1"
    assert ret[1].result() == "2"
    assert ret[2].result() is None

    # plugins not need to wait
    assert p.wait_for_plugins() is None

    # stop plugins
    p.stop()

    # clean up
    p.cleanup()


def test_phandler_start_poll(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
        DPluginDescription("plugin3", MockPlugin3),
    ]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # enable all plugins
    p.enable("plugin1", **{})
    p.enable("plugin2", **{})
    p.enable("plugin3", **{})
    assert len(p.enabled) == 3

    # start plugins
    p.start()

    # poll
    ret = p.poll()
    assert ret[0].result() == "1"
    assert ret[1].result() == "2"
    assert ret[2].result() is None

    # poll once again but all handled
    ret = p.poll()
    assert ret is None

    # plugins not need to wait
    assert p.wait_for_plugins() is None

    # stop plugins
    p.stop()

    # clean up
    p.cleanup()


def test_phandler_start_nostream(nxscope):
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # enable all plugins
    p.enable("plugin1", **{})
    assert len(p.enabled) == 1

    # start plugins
    p.start()

    ret = p.ready()
    assert ret[0].result() == "1"

    # plugins not need to wait
    assert p.wait_for_plugins() is None

    # stop plugins
    p.stop()

    # clean up
    p.cleanup()


def test_phandler_start_noready(nxscope):
    plugins = [DPluginDescription("plugin4", MockPlugin4)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # enable all plugins
    p.enable("plugin4", **{})
    assert len(p.enabled) == 1

    # start plugins
    p.start()

    # always not ready
    ret = p.ready()
    assert ret == []

    # always not ready
    ret = p.poll()
    assert ret == []

    # plugins not need to wait
    assert p.wait_for_plugins() is None

    # stop plugins
    p.stop()

    # clean up
    p.cleanup()


def test_phandler_trigger():
    p = PluginHandler()

    # default all on
    dt = p.trigger_get(0)
    assert dt.ttype == "on"
    assert dt.srcchan is None
    assert dt.params is None
    dt = p.trigger_get(1)
    assert dt.ttype == "on"
    assert dt.srcchan is None
    assert dt.params is None

    trg = {-1: DTriggerConfigReq("off", None)}
    p.triggers_configure(trg)
    dt = p.trigger_get(0)
    assert dt.ttype == "off"
    assert dt.srcchan is None
    assert dt.params is None
    dt = p.trigger_get(1)
    assert dt.ttype == "off"
    assert dt.srcchan is None
    assert dt.params is None

    trg = {-1: DTriggerConfigReq("on", None)}
    p.triggers_configure(trg)
    dt = p.trigger_get(0)
    assert dt.ttype == "on"
    assert dt.srcchan is None
    assert dt.params is None
    dt = p.trigger_get(1)
    assert dt.ttype == "on"
    assert dt.srcchan is None
    assert dt.params is None

    trg = {0: DTriggerConfigReq("on", None), 1: DTriggerConfigReq("off", None)}
    p.triggers_configure(trg)
    dt = p.trigger_get(0)
    assert dt.ttype == "on"
    assert dt.srcchan is None
    assert dt.params is None
    dt = p.trigger_get(1)
    assert dt.ttype == "off"
    assert dt.srcchan is None
    assert dt.params is None

    # clean up
    p.cleanup()
