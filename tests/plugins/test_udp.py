from nxscli.plugins.udp import PluginUdp


def test_pluginudp_init():
    plugin = PluginUdp()

    assert plugin.stream is True

    # TODO:
