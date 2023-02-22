"""The default Nxscli plugins handler."""

# TODO: dynamic load
from nxscli.iplugin import DPluginDescription
from nxscli.plugins.animation1 import PluginAnimation1
from nxscli.plugins.animation2 import PluginAnimation2
from nxscli.plugins.capture import PluginCapture
from nxscli.plugins.csv import PluginCsv
from nxscli.plugins.devinfo import PluginDevinfo
from nxscli.plugins.none import PluginNone
from nxscli.plugins.npmem import PluginNpmem
from nxscli.plugins.npsave import PluginNpsave

g_plugins_default = [
    DPluginDescription("devinfo", PluginDevinfo),
    DPluginDescription("capture", PluginCapture),
    DPluginDescription("animation1", PluginAnimation1),
    DPluginDescription("animation2", PluginAnimation2),
    DPluginDescription("csv", PluginCsv),
    DPluginDescription("npsave", PluginNpsave),
    DPluginDescription("npmem", PluginNpmem),
    DPluginDescription("none", PluginNone),
]
