from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.iplugin import DPluginDescription
from nxscli.phandler import PluginHandler
from nxscli.plugins.devinfo import PluginDevinfo


def test_plugindevinfo_init():
    plugin = PluginDevinfo()

    assert plugin.stream is False

    # TODO:


def test_plugindevinfo_content():
    intf = DummyDev()
    parse = Parser()
    with NxscopeHandler(intf, parse, enable_bitrate_tracking=True) as nxscope:
        with PluginHandler(
            [DPluginDescription("pdevinfo", PluginDevinfo)]
        ) as phandler:
            phandler.nxscope_connect(nxscope)

            plugin = PluginDevinfo()
            plugin.connect_phandler(phandler)

            assert plugin.start({}) is True
            out = plugin.result()

            assert "Device common" in out
            assert "Channels state (applied)" in out
            assert "Channels state (buffered)" in out
            assert "stream_started" in out
            assert "bitrate" in out
