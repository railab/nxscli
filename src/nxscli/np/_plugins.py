"""Numpy based plugins list."""

from nxscli.iplugin import DPluginDescription
from nxscli.np.commands.cmd_npmem import cmd_pnpmem
from nxscli.np.commands.cmd_npsave import cmd_pnpsave
from nxscli.np.plugins.npmem import PluginNpmem
from nxscli.np.plugins.npsave import PluginNpsave

plugins_list = [
    DPluginDescription("npsave", PluginNpsave, cmd_pnpsave),
    DPluginDescription("npmem", PluginNpmem, cmd_pnpmem),
]
