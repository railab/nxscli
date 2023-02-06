from nxscli.plugins.devinfo import PluginDevinfo


def test_plugindevinfo_init():
    plugin = PluginDevinfo()

    assert plugin.stream is False

    # TODO:
