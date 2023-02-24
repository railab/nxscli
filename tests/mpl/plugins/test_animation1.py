from nxscli.mpl.plugins.animation1 import PluginAnimation1


def test_pluginanimaton1_init():
    plugin = PluginAnimation1()

    assert plugin.stream is True

    # TODO:
