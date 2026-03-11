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


def test_phandler_nxscope_property(nxscope):
    """Test nxscope property access."""
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
    ]
    p = PluginHandler(plugins=plugins)

    # Test assertion when not connected
    with pytest.raises(AssertionError):
        _ = p.nxscope

    # Connect and test successful access
    p.nxscope_connect(nxscope)
    assert p.nxscope is not None
    assert p.nxscope == nxscope

    # Cleanup
    p.cleanup()


def test_phandler_nxscope_status_interfaces(nxscope):
    """Test status and capabilities interfaces from PluginHandler."""
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    caps = p.get_device_capabilities()
    assert caps.chmax > 0

    enabled = p.get_enabled_channels()
    assert enabled == ()

    dividers = p.get_channel_dividers()
    assert len(dividers) == caps.chmax

    state = p.get_channels_state()
    assert state.enabled_channels == ()
    assert len(state.dividers) == caps.chmax

    stats = p.get_stream_stats()
    assert stats.connected is True
    assert stats.stream_started is False

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


def test_phandler_collect_inputhooks():  # noqa: C901
    """Test collect_inputhooks method."""

    class PluginWithHook(IPlugin):  # pragma: no cover
        def __init__(self):
            super().__init__(EPluginType.ANIMATION)

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

        @classmethod
        def get_inputhook(cls):
            def hook(context):
                pass

            return hook

    class PluginWithoutHook(IPlugin):  # pragma: no cover
        def __init__(self):
            super().__init__(EPluginType.TEXT)

        @property
        def stream(self) -> bool:
            return False

        def stop(self) -> None:
            pass

        def data_wait(self, timeout=None) -> bool:
            return True

        def start(self, kwargs) -> bool:
            return True

        def result(self):
            return None

    # Create plugin handler with plugins
    plugins = [
        DPluginDescription("with_hook", PluginWithHook),
        DPluginDescription("without_hook", PluginWithoutHook),
    ]
    p = PluginHandler(plugins)

    # Collect inputhooks
    hooks = p.collect_inputhooks()

    # Should find one hook (from PluginWithHook)
    assert len(hooks) == 1
    assert callable(hooks[0])

    # clean up
    p.cleanup()


def test_phandler_plugin_start_stop_dynamic(nxscope):
    """Test plugin_start_dynamic and plugin_stop_dynamic methods."""
    nxscope.connect()
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # Start plugin dynamically (no chanlist configured)
    pid = p.plugin_start_dynamic("plugin1", channels=[0, 1])
    assert pid == 0
    assert len(p._started) == 1

    # Get started plugins
    started = p.get_started_plugins()
    assert len(started) == 1
    assert started[0] == (0, "plugin1")

    # Stop plugin dynamically
    p.plugin_stop_dynamic(pid)
    assert len(p._started) == 0

    # Test invalid PID
    with pytest.raises(IndexError):
        p.plugin_stop_dynamic(99)

    # clean up
    p.cleanup()


def test_phandler_get_started_plugins_unregistered():
    """Test get_started_plugins with unregistered plugin class."""
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    p = PluginHandler(plugins=plugins)

    # Manually create a plugin instance not in _plugins
    plugin = MockPlugin2()
    p._started.append((plugin, {}))

    # Should fall back to class name
    started = p.get_started_plugins()
    assert len(started) == 1
    assert started[0] == (0, "MockPlugin2")

    # clean up
    p.cleanup()


def test_phandler_plugin_start_dynamic_all_channels(nxscope):
    """Test plugin_start_dynamic with -1 (all channels)."""
    nxscope.connect()
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    # Start plugin with -1 to select all channels
    pid = p.plugin_start_dynamic("plugin1", channels=[-1])
    assert pid == 0

    # Stop plugin
    p.plugin_stop_dynamic(pid)

    # clean up
    p.cleanup()


def test_phandler_plugin_start_dynamic_plot_plugin(nxscope):
    """Test plugin_start_dynamic for plot plugin branch."""
    nxscope.connect()
    plugins = [DPluginDescription("plugin3", MockPlugin3)]
    p = PluginHandler(plugins=plugins)
    p.nxscope_connect(nxscope)

    pid = p.plugin_start_dynamic("plugin3", channels=[0])
    assert pid == 0
    assert len(p._started) == 1

    p.plugin_stop_dynamic(pid)
    p.cleanup()


def test_phandler_chanlist_plugin_dynamic_mode(nxscope):
    """Test chanlist_plugin in dynamic mode (no chanlist configured)."""
    nxscope.connect()
    p = PluginHandler()
    p.nxscope_connect(nxscope)

    # Don't configure channels - this puts us in dynamic mode
    # _chanlist should be empty

    # Test with -1 (all channels)
    chanlist = p.chanlist_plugin([-1])
    assert len(chanlist) > 0
    assert all(ch.data.is_valid for ch in chanlist)

    # Test with specific channels
    chanlist = p.chanlist_plugin([0, 1, 2])
    assert len(chanlist) <= 3
    assert all(ch.data.is_valid for ch in chanlist)

    # Test with a channel that might not exist (high channel ID)
    # This tests the branch where ch might be None or not valid
    chanlist = p.chanlist_plugin([0, 999])
    assert len(chanlist) <= 2

    # clean up
    p.cleanup()
