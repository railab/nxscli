"""Plugins loader."""

import importlib
from importlib.metadata import entry_points

plugins_list = []
configs_list = []

# load default plugins
module = "nxscli._plugins"
mod = importlib.import_module(module)

# default plugins
plugins_list.extend(mod.plugins_list)
# default configuration commands
configs_list.extend(mod.configs_list)

# load external plugins
eps = entry_points(group="nxscli.extensions")
for entry in eps:  # pragma: no cover
    print("loading ", entry.name, "...")
    plugin = eps[entry.name].load()
    plugins_list.extend(plugin.plugins_list)
    configs_list.extend(plugin.configs_list)
