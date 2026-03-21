from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.iplugin import DPluginDescription
from nxscli.phandler import PluginHandler
from nxscli.plugins.devinfo import PluginDevinfo


def test_plugindevinfo_init():
    plugin = PluginDevinfo()

    assert plugin.stream is False
    assert plugin.data_wait() is True


def test_plugindevinfo_helpers():
    assert PluginDevinfo._get_bool({}, "missing") is False
    assert PluginDevinfo._get_bool({"flag": 1}, "flag") is True

    assert PluginDevinfo._get_int({}, "missing") == 0
    assert PluginDevinfo._get_int({"value": "7"}, "value") == 7

    assert PluginDevinfo._get_float({}, "missing") == 0.0
    assert PluginDevinfo._get_float({"value": "1.5"}, "value") == 1.5

    assert PluginDevinfo._format_bool(True) == "yes"
    assert PluginDevinfo._format_bool(False) == "no"

    assert PluginDevinfo._format_enabled(()) == "none"
    assert PluginDevinfo._format_enabled((3,)) == "3"
    assert PluginDevinfo._format_enabled((1, 2, 3, 5, 7, 8)) == "1-3, 5, 7-8"


def test_plugindevinfo_table_render():
    out = PluginDevinfo._render_channels_table(
        [
            {
                "chan": 10,
                "name": "",
                "dtype_text": "UNDEF",
                "vdim": 0,
                "valid": False,
                "enabled": False,
                "divider": 0,
            }
        ]
    )

    assert "Valid" in out
    assert "| 10 |" in out
    assert "UNDEF" in out
    assert "| no" in out


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

            assert "Device Summary" in out
            assert "Channel State" in out
            assert "Applied enabled:  none" in out
            assert "Bitrate:          0.0 B/s" in out
            assert "noise_uniform_scalar" in out
            assert "FLOAT" in out
            assert "| 10 |" in out
            assert "UNDEF" in out
