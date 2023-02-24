from nxscli.mpl.plugins.capture import PluginCapture


def test_plugincapture_init():
    plugin = PluginCapture()

    assert plugin.stream is True

    # TODO:
