"""Module containint the CLI logic for Nxslib."""

import sys
from typing import Any

import click
from nxslib.proto.parse import Parser

from nxscli.cli.environment import Environment, pass_environment
from nxscli.iplugin import EPluginType, IPlugin
from nxscli.logger import logger
from nxscli.phandler import PluginHandler
from nxscli.plugins_loader import commands_list, interfaces_list, plugins_list

###############################################################################
# Function: main
###############################################################################


@click.group()
@click.option(
    "--debug/--no-debug",
    default=False,
    is_flag=True,
    envvar="NXSCLI_DEBUG",
)
@pass_environment
def main(ctx: Environment, debug: bool) -> bool:
    """Nxscli - Command-line clinet to the NxScope."""
    ctx.debug = debug
    if debug:  # pragma: no cover
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

    ctx.phandler = PluginHandler(plugins_list)
    parse = Parser()
    ctx.parser = parse
    ctx.triggers = {}

    click.get_current_context().call_on_close(cli_on_close)

    return True


###############################################################################
# Function: handle_plugin
###############################################################################


def handle_plugin(plugin: IPlugin) -> tuple[EPluginType, Any] | None:
    """Handle a given plugin."""
    if plugin.ptype == EPluginType.TEXT:
        # print output
        print(plugin.result())
        return None

    elif plugin.ptype == EPluginType.STATIC:  # pragma: no cover
        plot = plugin.result()
        return (EPluginType.STATIC, plot)

    elif plugin.ptype == EPluginType.ANIMATION:  # pragma: no cover
        plot = plugin.result()
        return (EPluginType.ANIMATION, plot)

    elif plugin.ptype == EPluginType.FILE:
        return None

    elif plugin.ptype == EPluginType.NONE:
        return None

    else:
        raise AssertionError


###############################################################################
# Function: plugin_loop
###############################################################################


def plugin_loop(ctx: Environment) -> list[Any]:
    """Plugin loop."""
    assert ctx.phandler
    ret: list[Any] = []
    while True:
        plugins = ctx.phandler.poll()
        if plugins is None:
            break

        if len(plugins) > 0:
            for x in plugins:
                r = handle_plugin(x)
                if ret:  # pragma: no cover
                    ret.append(r)
        else:  # pragma: no cover
            pass

    return ret


###############################################################################
# Function: wait_for_plugins
###############################################################################


def wait_for_plugins(ctx: Environment) -> None:  # pragma: no cover
    """Wait for plugins."""
    assert ctx.phandler
    ctx.phandler.wait_for_plugins()


###############################################################################
# Function: cli_on_close
###############################################################################


@pass_environment
def cli_on_close(ctx: Environment) -> bool:
    """Handle requested plugins on click close."""
    assert ctx.phandler
    # do not show any errors if it was help request
    if "--help" in sys.argv:  # pragma: no cover
        ctx.phandler.cleanup()
        return True

    if ctx.interface is False:
        ctx.phandler.cleanup()
        return False

    if len(ctx.phandler.enabled) == 0:
        click.secho("ERROR: No plugins selected !", err=True, fg="red")
        ctx.phandler.cleanup()
        return False

    if ctx.needchannels:
        if ctx.channels is None:  # pragma: no cover
            click.secho("ERROR: No channels selected !", err=True, fg="red")
            ctx.phandler.cleanup()
            return False

    # connect nxscope to phandler
    assert ctx.nxscope
    ctx.phandler.nxscope_connect(ctx.nxscope)

    # configure channles after connected to nxscope
    if ctx.needchannels and ctx.channels:
        ctx.phandler.channels_configure(ctx.channels[0], ctx.channels[1])

    # start plugins
    ctx.phandler.start()

    if ctx.waitenter:  # pragma: no cover
        _ = input("wait for Enter key...")

    # plugins loop
    plugin_loop(ctx)

    # wait for plugin
    wait_for_plugins(ctx)

    print("closing...")
    ctx.phandler.stop()
    ctx.phandler.nxscope_disconnect()
    ctx.phandler.cleanup()

    return True


###############################################################################
# Function: click_final_init
###############################################################################


def click_final_init() -> None:
    """Handle final Click initialization."""
    # add interfaces
    for intf in interfaces_list:
        main.add_command(intf)

    # add commands to interfaces
    for group in interfaces_list:
        for cmd in commands_list:
            group.add_command(cmd)


# final click initialization
click_final_init()
