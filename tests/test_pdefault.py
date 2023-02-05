from nxscli.pdefault import g_plugins_default


def test_nxsclipdefault_init():
    assert isinstance(g_plugins_default, list)
