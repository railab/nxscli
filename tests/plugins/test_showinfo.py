from nxscli.plugins.showinfo import PluginShowinfo


def test_pluginshowinfo_init():
    plugin = PluginShowinfo()

    assert plugin.stream is False

    # TODO:
