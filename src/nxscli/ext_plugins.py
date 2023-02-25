"""Default plugins."""

from nxscli.iplugin import DPluginDescription
from nxscli.plugins.csv import PluginCsv
from nxscli.plugins.devinfo import PluginDevinfo
from nxscli.plugins.none import PluginNone
from nxscli.plugins.printer import PluginPrinter

plugins_list = [
    DPluginDescription("devinfo", PluginDevinfo),
    DPluginDescription("csv", PluginCsv),
    DPluginDescription("none", PluginNone),
    DPluginDescription("printer", PluginPrinter),
]
