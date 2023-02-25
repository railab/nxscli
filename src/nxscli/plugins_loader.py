"""Plugins loader."""

from importlib.metadata import entry_points

import nxscli.plugin

plugins_list = []
configs_list = []
interfaces_list = []

# default plugins
plugins_list.extend(nxscli.plugin.plugins_list)
# default configuration commands
configs_list.extend(nxscli.plugin.configs_list)
# default interfaces commands
interfaces_list.extend(nxscli.plugin.interfaces_list)

# load external plugins
eps = entry_points(group="nxscli.extensions")
for entry in eps:  # pragma: no cover
    print("loading ", entry.name, "...")
    plugin = eps[entry.name].load()
    plugins_list.extend(plugin.plugins_list)
    configs_list.extend(plugin.configs_list)
