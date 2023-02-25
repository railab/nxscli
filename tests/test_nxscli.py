import nxscli
import nxscli.ext_commands
import nxscli.ext_interfaces
import nxscli.ext_plugins


def test_extplugins():
    assert nxscli.__version__

    assert isinstance(nxscli.ext_plugins.plugins_list, list)
    assert isinstance(nxscli.ext_commands.commands_list, list)
    assert isinstance(nxscli.ext_interfaces.interfaces_list, list)
