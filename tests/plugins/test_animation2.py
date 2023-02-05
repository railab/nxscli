from nxscli.plugins.animation2 import PluginAnimation2


def test_pluginanimaton2_init():
    plugin = PluginAnimation2()

    assert plugin.stream is True

    # TODO:
