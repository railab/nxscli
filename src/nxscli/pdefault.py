"""The default Nxscli plugins handler."""

# TODO: dynamic load
from nxscli.iplugin import DPluginDescription
from nxscli.plugins.animation1 import PluginAnimation1, pani1
from nxscli.plugins.animation2 import PluginAnimation2, pani2
from nxscli.plugins.capture import PluginCapture, pcap
from nxscli.plugins.csv import PluginCsv, pcsv
from nxscli.plugins.devinfo import PluginDevinfo, pdevinfo
from nxscli.plugins.none import PluginNone, pnone
from nxscli.plugins.npmem import PluginNpmem, pnpmem
from nxscli.plugins.npsave import PluginNpsave, pnpsave

g_plugins_default = [
    DPluginDescription("devinfo", PluginDevinfo, pdevinfo),
    DPluginDescription("capture", PluginCapture, pcap),
    DPluginDescription("animation1", PluginAnimation1, pani1),
    DPluginDescription("animation2", PluginAnimation2, pani2),
    DPluginDescription("csv", PluginCsv, pcsv),
    DPluginDescription("npsave", PluginNpsave, pnpsave),
    DPluginDescription("npmem", PluginNpmem, pnpmem),
    DPluginDescription("none", PluginNone, pnone),
]
