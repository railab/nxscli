"""The default Nxscli plugins handler."""

# TODO: dynamic load
from nxscli.iplugin import DPluginDescription
from nxscli.plugins.animation1 import PluginAnimation1, cmd_pani1
from nxscli.plugins.animation2 import PluginAnimation2, cmd_pani2
from nxscli.plugins.capture import PluginCapture, cmd_pcap
from nxscli.plugins.csv import PluginCsv, cmd_pcsv
from nxscli.plugins.devinfo import PluginDevinfo, cmd_pdevinfo
from nxscli.plugins.none import PluginNone, cmd_pnone
from nxscli.plugins.npmem import PluginNpmem, cmd_pnpmem
from nxscli.plugins.npsave import PluginNpsave, cmd_pnpsave

g_plugins_default = [
    DPluginDescription("devinfo", PluginDevinfo, cmd_pdevinfo),
    DPluginDescription("capture", PluginCapture, cmd_pcap),
    DPluginDescription("animation1", PluginAnimation1, cmd_pani1),
    DPluginDescription("animation2", PluginAnimation2, cmd_pani2),
    DPluginDescription("csv", PluginCsv, cmd_pcsv),
    DPluginDescription("npsave", PluginNpsave, cmd_pnpsave),
    DPluginDescription("npmem", PluginNpmem, cmd_pnpmem),
    DPluginDescription("none", PluginNone, cmd_pnone),
]
