"""Plugins loader."""

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

import nxscli.ext_commands
import nxscli.ext_interfaces
import nxscli.ext_plugins
from nxscli.logger import logger

if TYPE_CHECKING:
    import click

    from nxscli.iplugin import DPluginDescription

plugins_list: list["DPluginDescription"] = []
commands_list: list["click.Command"] = []
interfaces_list: list["click.Group"] = []

# default plugins
plugins_list.extend(nxscli.ext_plugins.plugins_list)
# default commands
commands_list.extend(nxscli.ext_commands.commands_list)
# default interfaces
interfaces_list.extend(nxscli.ext_interfaces.interfaces_list)

# load external plugins
eps = entry_points(group="nxscli.extensions")
for entry in eps:  # pragma: no cover
    logger.info("loading %s %s ...", entry.name, entry.value)
    plugin = entry.load()
    if entry.name == "plugins":
        plugins_list.extend(plugin.plugins_list)
    elif entry.name == "commands":
        commands_list.extend(plugin.commands_list)
    elif entry.name == "interfaces":
        interfaces_list.extend(plugin.interfaces_list)
    else:
        raise AssertionError("Unsupported entry name")
