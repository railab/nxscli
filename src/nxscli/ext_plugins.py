"""Default plugins."""

from nxscli.iplugin import DPluginDescription
from nxscli.plugins.csv import PluginCsv
from nxscli.plugins.devinfo import PluginDevinfo
from nxscli.plugins.none import PluginNone
from nxscli.plugins.printer import PluginPrinter
from nxscli.plugins.udp import PluginUdp

plugins_list = [
    DPluginDescription("devinfo", PluginDevinfo),
    DPluginDescription("csv", PluginCsv),
    DPluginDescription("none", PluginNone),
    DPluginDescription("printer", PluginPrinter),
    DPluginDescription("udp", PluginUdp),
]
