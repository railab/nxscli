"""Plugins loader."""

import importlib

plugins_list = []

# load default plugins
module = "nxscli._plugins"
mod = importlib.import_module(module)
plugins_list.extend(mod.plugins_list)

# load packages - one day they will be separate Python packages
plugin_packages = ["mpl", "np"]
for package in plugin_packages:
    module = f"nxscli.{package}._plugins"
    mod = importlib.import_module(module)
    plugins_list.extend(mod.plugins_list)
