from nxscli.np.plugins.npsave import PluginNpsave


def test_pluginnpsave_init():
    plugin = PluginNpsave()

    assert plugin.stream is True

    # TODO:
