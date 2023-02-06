"""The default Nxscli plugins handler."""

# TODO: dynamic load
from nxscli.plugins.animation1 import PluginAnimation1
from nxscli.plugins.animation2 import PluginAnimation2
from nxscli.plugins.capture import PluginCapture
from nxscli.plugins.csv import PluginCsv
from nxscli.plugins.devinfo import PluginDevinfo

g_plugins_default = [
    ["devinfo", PluginDevinfo],
    ["capture", PluginCapture],
    ["animation1", PluginAnimation1],
    ["animation2", PluginAnimation2],
    ["csv", PluginCsv],
]
