"""Matplotlib based plugins list."""

from nxscli.iplugin import DPluginDescription
from nxscli.mpl.plugins.animation1 import PluginAnimation1, cmd_pani1
from nxscli.mpl.plugins.animation2 import PluginAnimation2, cmd_pani2
from nxscli.mpl.plugins.capture import PluginCapture, cmd_pcap

plugins_list = [
    DPluginDescription("capture", PluginCapture, cmd_pcap),
    DPluginDescription("animation1", PluginAnimation1, cmd_pani1),
    DPluginDescription("animation2", PluginAnimation2, cmd_pani2),
]
