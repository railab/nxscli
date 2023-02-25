import nxscli
import nxscli.plugin


def test_nxscli():
    assert nxscli.__version__

    assert isinstance(nxscli.plugin.plugins_list, list)
    assert isinstance(nxscli.plugin.configs_list, list)
    assert isinstance(nxscli.plugin.interfaces_list, list)
