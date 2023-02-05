from nxscli.plugins.csv import PluginCsv


def test_plugincsv_init():
    plugin = PluginCsv()

    assert plugin.stream is True

    # TODO:
