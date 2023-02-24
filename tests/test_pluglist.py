from nxscli.pluglist import plugins_list


def test_nxsclipluglist_init():
    assert isinstance(plugins_list, list)
