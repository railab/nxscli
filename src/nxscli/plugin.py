"""Default plugins and commands."""

from nxscli.commands.cmd_config import cmd_chan, cmd_trig
from nxscli.commands.cmd_csv import cmd_pcsv
from nxscli.commands.cmd_devinfo import cmd_pdevinfo
from nxscli.commands.cmd_interface import cmd_dummy, cmd_serial
from nxscli.commands.cmd_none import cmd_pnone
from nxscli.commands.cmd_printer import cmd_printer
from nxscli.iplugin import DPluginDescription
from nxscli.plugins.csv import PluginCsv
from nxscli.plugins.devinfo import PluginDevinfo
from nxscli.plugins.none import PluginNone
from nxscli.plugins.printer import PluginPrinter

plugins_list = [
    DPluginDescription("devinfo", PluginDevinfo, cmd_pdevinfo),
    DPluginDescription("csv", PluginCsv, cmd_pcsv),
    DPluginDescription("none", PluginNone, cmd_pnone),
    DPluginDescription("printer", PluginPrinter, cmd_printer),
]

configs_list = [cmd_chan, cmd_trig]
interfaces_list = [cmd_serial, cmd_dummy]
