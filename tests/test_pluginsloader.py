from nxscli.plugins_loader import plugins_list


def test_pluginsloader_init():
    assert isinstance(plugins_list, list)
