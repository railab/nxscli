import queue
from types import SimpleNamespace

import pytest  # type: ignore
from nxslib.dev import DeviceChannel

from nxscli.channelref import ChannelRef
from nxscli.iplugin import (
    DPluginDescription,
    EPluginType,
    IPlugin,
    IPluginPlotDynamic,
    IPluginPlotStatic,
    IPluginText,
)
from nxscli.phandler import PluginHandler
from nxscli.plugins.none import PluginNone
from nxscli.trigger import DTriggerConfigReq
from tests.fake_nxscope import FakeNxscope


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
    with PluginHandler([]) as p:
        assert isinstance(p, PluginHandler)
        assert p.names == []

    # valid data
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    with PluginHandler(plugins=plugins) as p:
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


@pytest.fixture
def nxscope():
    nxscope = FakeNxscope()
    yield nxscope
    nxscope.disconnect()


def test_phandler_connect(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_nxscope_property(nxscope):
    """Test nxscope property access."""
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
    ]
    with PluginHandler(plugins=plugins) as p:
        # Test assertion when not connected
        with pytest.raises(AssertionError):
            _ = p.nxscope

        # Connect and test successful access
        p.nxscope_connect(nxscope)
        assert p.nxscope is not None
        assert p.nxscope == nxscope


def test_phandler_nxscope_status_interfaces(nxscope):
    """Test status and capabilities interfaces from PluginHandler."""
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_enable():
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
    ]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_start_ready(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
        DPluginDescription("plugin3", MockPlugin3),
    ]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_start_poll(nxscope):
    plugins = [
        DPluginDescription("plugin1", MockPlugin1),
        DPluginDescription("plugin2", MockPlugin2),
        DPluginDescription("plugin3", MockPlugin3),
    ]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_start_nostream(nxscope):
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_start_noready(nxscope):
    plugins = [DPluginDescription("plugin4", MockPlugin4)]
    with PluginHandler(plugins=plugins) as p:
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


def test_phandler_trigger():
    with PluginHandler() as p:
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

        trg = {
            0: DTriggerConfigReq("on", None),
            1: DTriggerConfigReq("off", None),
        }
        p.triggers_configure(trg)
        dt = p.trigger_get(0)
        assert dt.ttype == "on"
        assert dt.srcchan is None
        assert dt.params is None
        dt = p.trigger_get(1)
        assert dt.ttype == "off"
        assert dt.srcchan is None
        assert dt.params is None


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
    with PluginHandler(plugins) as p:
        # Collect inputhooks
        hooks = p.collect_inputhooks()

        # Should find one hook (from PluginWithHook)
        assert len(hooks) == 1
        assert callable(hooks[0])


def test_phandler_plugin_start_stop_dynamic(nxscope):
    """Test plugin_start_dynamic and plugin_stop_dynamic methods."""
    with nxscope:
        plugins = [DPluginDescription("plugin1", MockPlugin1)]
        with PluginHandler(plugins=plugins) as p:
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
            pytest.raises(IndexError, p.plugin_stop_dynamic, 99)


def test_phandler_get_started_plugins_unregistered():
    """Test get_started_plugins with unregistered plugin class."""
    plugins = [DPluginDescription("plugin1", MockPlugin1)]
    with PluginHandler(plugins=plugins) as p:
        # Manually create a plugin instance not in _plugins
        plugin = MockPlugin2()
        p._started.append((plugin, {}))

        # Should fall back to class name
        started = p.get_started_plugins()
        assert len(started) == 1
        assert started[0] == (0, "MockPlugin2")


def test_phandler_plugin_start_dynamic_all_channels(nxscope):
    """Test plugin_start_dynamic with -1 (all channels)."""
    with nxscope:
        plugins = [DPluginDescription("plugin1", MockPlugin1)]
        with PluginHandler(plugins=plugins) as p:
            p.nxscope_connect(nxscope)

            # Start plugin with -1 to select all channels
            pid = p.plugin_start_dynamic("plugin1", channels=[-1])
            assert pid == 0

            # Stop plugin
            p.plugin_stop_dynamic(pid)


def test_phandler_plugin_start_dynamic_plot_plugin(nxscope):
    """Test plugin_start_dynamic for plot plugin branch."""
    with nxscope:
        plugins = [DPluginDescription("plugin3", MockPlugin3)]
        with PluginHandler(plugins=plugins) as p:
            p.nxscope_connect(nxscope)

            pid = p.plugin_start_dynamic("plugin3", channels=[0])
            assert pid == 0
            assert len(p._started) == 1

            p.plugin_stop_dynamic(pid)


def test_phandler_chanlist_plugin_dynamic_mode(nxscope):
    """Test chanlist_plugin in dynamic mode (no chanlist configured)."""
    with nxscope:
        with PluginHandler() as p:
            p.nxscope_connect(nxscope)

            # Don't configure channels - this puts us in dynamic mode
            # _chanlist should be empty

            # Test with -1 (all channels)
            chanlist = p.chanlist_plugin([ChannelRef.all_channels()])
            assert len(chanlist) > 0
            assert all(ch.data.is_valid for ch in chanlist)

            # Test with specific channels
            chanlist = p.chanlist_plugin(
                [
                    ChannelRef.physical(0),
                    ChannelRef.physical(1),
                    ChannelRef.physical(2),
                ]
            )
            assert len(chanlist) <= 3
            assert all(ch.data.is_valid for ch in chanlist)

            # Test with a channel that might not exist (high channel ID)
            # This tests the branch where ch might be None or not valid
            chanlist = p.chanlist_plugin(
                [ChannelRef.physical(0), ChannelRef.physical(999)]
            )
            assert len(chanlist) <= 2


class _MockProvider:
    def __init__(self) -> None:
        self.connected = False
        self.started = False
        self.channels = {}
        self.subs = []

    def on_connect(self, nxscope) -> None:
        del nxscope
        self.connected = True

    def on_disconnect(self) -> None:
        self.connected = False

    def on_stream_start(self) -> None:
        self.started = True

    def on_stream_stop(self) -> None:
        self.started = False

    def channel_get(self, channel):
        if channel.is_virtual:
            return self.channels.get(channel.virtual_name())
        return None

    def channel_list(self):
        return tuple(self.channels.values())

    def stream_sub(self, channel):
        if not channel.is_virtual:
            return None
        chan = channel.virtual_name()
        if chan not in self.channels:
            return None
        q = queue.Queue()
        self.subs.append(q)
        return q

    def stream_unsub(self, subq) -> bool:
        if subq in self.subs:
            self.subs.remove(subq)
            return True
        return False


def test_phandler_stream_provider(nxscope):
    with PluginHandler() as p:
        provider = _MockProvider()
        provider.channels["v0"] = DeviceChannel(-2, 10, 1, "v0")
        provider.channels["vinvalid"] = DeviceChannel(-4, 0, 1, "vinvalid")

        p.stream_provider_add(provider)
        p.service_set("k", "v")
        assert p.service_get("k") == "v"
        assert p.channel_get(ChannelRef.virtual(0)) is not None

        p.nxscope_connect(nxscope)
        provider2 = _MockProvider()
        provider2.channels["v1"] = DeviceChannel(-3, 10, 1, "v1")
        p.stream_provider_add(provider2)
        assert p.channel_get(ChannelRef.virtual(1)) is not None
        assert provider.connected is True
        all_channels = p.chanlist_plugin([ChannelRef.all_channels()])
        assert any(ch.data.chan == -2 for ch in all_channels)
        p.channels_configure([ChannelRef.virtual(0)], div=1, writenow=True)
        p.channels_configure([ChannelRef.virtual(0)], div=[1], writenow=True)
        p._chanlist_enable()
        p.stream_start()
        assert provider.started is True

        sub = p.stream_sub(ChannelRef.virtual(0))
        assert isinstance(sub, queue.Queue)
        p.stream_unsub(sub)

        p.stream_stop()
        assert provider.started is False


def test_phandler_stream_unsub_fallback(nxscope):
    with PluginHandler() as p:
        provider = _MockProvider()
        p.stream_provider_add(provider)
        p.nxscope_connect(nxscope)
        subq = p.stream_sub(ChannelRef.physical(0))
        p.stream_unsub(subq)


def test_phandler_provider_channel_get_fallbacks(nxscope):
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        provider1 = _MockProvider()
        provider2 = _MockProvider()
        provider2.channels["v0"] = DeviceChannel(-2, 10, 1, "v0")

        p.stream_provider_add(provider1)
        p.stream_provider_add(provider2)

        assert p.channel_get(ChannelRef.virtual(0)) is not None
        assert p.channel_get(ChannelRef.virtual(42)) is None


def test_phandler_enable_and_div_skip_virtual(nxscope):
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)
        phys = p.channel_get(ChannelRef.physical(0))
        assert phys is not None
        virt = DeviceChannel(-2, 10, 1, "v0")
        p._chanlist = [virt, phys]

        p._chanlist_enable()
        enabled = p.get_enabled_channels(applied=False)
        assert 0 in enabled

        p._chanlist_div(1)
        p._chanlist_div([0, 1])
        assert p.get_channel_divider(0, applied=False) == 1


def test_phandler_channel_ref_parser_branches() -> None:
    with PluginHandler() as p:
        assert p._channel_ref(-1).is_all
        assert p._channel_ref("2").physical_id() == 2
        assert p._channel_ref("v7").virtual_name() == "v7"
        assert p._channel_refs(None, default_all=False) == []

        with pytest.raises(ValueError):
            p._channel_ref("vA")

        with pytest.raises(ValueError):
            p._channel_ref("bad")


def test_phandler_stream_sub_nonphysical_raises(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        with pytest.raises(ValueError):
            p.stream_sub(ChannelRef.virtual(99))


def test_phandler_enable_div_skip_nonexistent_channels(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        missing = DeviceChannel(999, 10, 1, "missing")
        p._chanlist = [missing]
        p._chanlist_enable()
        p._chanlist_div(1)
        p._chanlist_div([1])


def test_phandler_chanlist_plugin_virtual_in_configured_mode(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        provider = _MockProvider()
        provider.channels["v0"] = DeviceChannel(-2, 10, 1, "v0")
        p.stream_provider_add(provider)
        p.channels_configure([ChannelRef.physical(0)], div=0, writenow=False)

        chanlist = p.chanlist_plugin([ChannelRef.virtual(0)])
        assert any(ch.data.chan == -2 for ch in chanlist)


def test_phandler_chanlist_plugin_virtual_multi_refs(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        provider = _MockProvider()
        provider.channels["v0"] = DeviceChannel(-2, 10, 1, "v0")
        p.stream_provider_add(provider)
        p.channels_configure([ChannelRef.physical(0)], div=0, writenow=False)

        chanlist = p.chanlist_plugin(
            [ChannelRef.virtual(42), ChannelRef.virtual(0)]
        )
        assert any(ch.data.chan == -2 for ch in chanlist)


def test_mock_provider_non_virtual_paths() -> None:
    provider = _MockProvider()
    assert provider.channel_get(ChannelRef.physical(0)) is None
    assert provider.stream_sub(ChannelRef.physical(0)) is None
    assert provider.stream_sub(ChannelRef.virtual(0)) is None


def test_phandler_chanlist_plugin_mixed_refs(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)

        provider = _MockProvider()
        provider.channels["v0"] = DeviceChannel(-2, 10, 1, "v0")
        p.stream_provider_add(provider)
        p.channels_configure([ChannelRef.physical(0)], div=0, writenow=False)

        chanlist = p.chanlist_plugin(
            [ChannelRef.physical(0), ChannelRef.virtual(0)]
        )
        assert any(ch.data.chan == -2 for ch in chanlist)
        assert any(ch.data.chan == 0 for ch in chanlist)


def test_phandler_stream_unsub_without_nxscope() -> None:
    with PluginHandler() as p:
        p.stream_unsub(queue.Queue())


def test_phandler_chanlist_plugin_all_skips_missing_channel(nxscope) -> None:
    with PluginHandler() as p:
        p.nxscope_connect(nxscope)
        dev_channel_get = nxscope.dev_channel_get

        def wrapped(chid: int):
            if chid == 1:
                return None
            return dev_channel_get(chid)

        nxscope.dev_channel_get = wrapped

        chanlist = p.chanlist_plugin([ChannelRef.all_channels()])
        assert all(ch.data.chan != 1 for ch in chanlist)


def test_pluginthread_is_done_partial() -> None:
    plugin = PluginNone()
    plugin._samples = 2
    plugin._nostop = False
    assert plugin._is_done([1]) is False


def test_pluginthread_common_not_done_path() -> None:
    class _QD:
        def queue_get(self, block, timeout=1.0):
            del block, timeout
            return [SimpleNamespace(data=[1.0], meta=[0])]

    plugin = PluginNone()
    plugin._samples = 2
    plugin._nostop = False
    plugin._datalen = [0]
    plugin._plugindata = SimpleNamespace(qdlist=[_QD()])

    plugin._thread_common()
    assert plugin._datalen == [1]
