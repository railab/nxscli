"""Default plugins."""

# TODO: dynamic load
from nxscli.iplugin import DPluginDescription
from nxscli.plugins.csv import PluginCsv, cmd_pcsv
from nxscli.plugins.devinfo import PluginDevinfo, cmd_pdevinfo
from nxscli.plugins.none import PluginNone, cmd_pnone
from nxscli.plugins.printer import PluginPrinter, cmd_printer

plugins_list = [
    DPluginDescription("devinfo", PluginDevinfo, cmd_pdevinfo),
    DPluginDescription("csv", PluginCsv, cmd_pcsv),
    DPluginDescription("none", PluginNone, cmd_pnone),
    DPluginDescription("printer", PluginPrinter, cmd_printer),
]
