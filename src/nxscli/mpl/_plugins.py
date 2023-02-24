"""Matplotlib based plugins list."""

from nxscli.iplugin import DPluginDescription
from nxscli.mpl.commands.cmd_ani1 import cmd_pani1
from nxscli.mpl.commands.cmd_ani2 import cmd_pani2
from nxscli.mpl.commands.cmd_cap import cmd_pcap
from nxscli.mpl.plugins.animation1 import PluginAnimation1
from nxscli.mpl.plugins.animation2 import PluginAnimation2
from nxscli.mpl.plugins.capture import PluginCapture

plugins_list = [
    DPluginDescription("capture", PluginCapture, cmd_pcap),
    DPluginDescription("animation1", PluginAnimation1, cmd_pani1),
    DPluginDescription("animation2", PluginAnimation2, cmd_pani2),
]
