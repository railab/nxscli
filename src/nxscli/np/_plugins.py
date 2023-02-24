"""Numpy based plugins list."""

from nxscli.iplugin import DPluginDescription
from nxscli.np.plugins.npmem import PluginNpmem, cmd_pnpmem
from nxscli.np.plugins.npsave import PluginNpsave, cmd_pnpsave

plugins_list = [
    DPluginDescription("npsave", PluginNpsave, cmd_pnpsave),
    DPluginDescription("npmem", PluginNpmem, cmd_pnpmem),
]
