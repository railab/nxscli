"""Module containint the CLI logic for Nxslib."""

import pprint
import sys
from typing import Any

import click
from nxslib.proto.parse import Parser

from nxscli.iplugin import EPluginType, IPlugin
from nxscli.logger import logger
from nxscli.main.cmd_config import cmd_chan, cmd_trig
from nxscli.main.cmd_interface import cmd_dummy, cmd_serial
from nxscli.main.environment import Environment, pass_environment
from nxscli.pdefault import g_plugins_default
from nxscli.phandler import PluginHandler
from nxscli.plot_mpl import MplManager, cmd_mpl

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

    ctx.phandler = PluginHandler(g_plugins_default)
    parse = Parser()
    ctx.parser = parse
    ctx.triggers = {}

    click.get_current_context().call_on_close(cli_on_close)

    return True


###############################################################################
# Function: devinfo_print
###############################################################################


def devinfo_print(info: dict[str, str]) -> None:
    """Print device information."""
    print("\nDevice common:\n")
    pprint.pprint(info["cmn"])
    print("\nDevice channels:")
    pprint.pprint(info["channels"])
    print("\n")


###############################################################################
# Function: handle_plugin
###############################################################################


def handle_plugin(plugin: IPlugin) -> tuple[EPluginType, Any] | None:
    """Handle a given plugin."""
    if plugin.ptype == EPluginType.TEXT:
        # REVISIT: only devinfo supported for now
        info = plugin.result()
        devinfo_print(info)
        return None

    elif plugin.ptype == EPluginType.STATIC:
        plot = plugin.result()
        for pdata in plot.plist:
            # plot samples
            pdata.plot()
        MplManager.show(block=False)
        return (EPluginType.STATIC, plot)

    elif plugin.ptype == EPluginType.ANIMATION:
        plot = plugin.result()
        MplManager.show(block=False)
        return (EPluginType.ANIMATION, plot)

    elif plugin.ptype == EPluginType.FILE:
        print("TODO: file handler ?")
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


def wait_for_plugins(ret: list[Any]) -> None:
    """Wait for plugins."""
    while True:  # pragma: no cover
        fig_open = False
        if MplManager.fig_is_open():
            fig_open = True
        # no fig opened - we can exit
        if not fig_open:
            break
        # pause
        MplManager.pause(1)


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

    # configure mplt
    if not ctx.mplstyle:  # pragma: no cover
        ctx.mplstyle = ["ggplot", "fast"]
    MplManager.mpl_config(ctx.mplstyle)

    # start plugins
    ctx.phandler.start()

    if ctx.waitenter:  # pragma: no cover
        _ = input("wait for Enter key...")

    # plugins loop
    ret = plugin_loop(ctx)

    # wait until all figers closed
    wait_for_plugins(ret)

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
    # interface commands
    interfaces = [cmd_dummy, cmd_serial]
    for intf in interfaces:
        main.add_command(intf)

    # config commands
    config = [cmd_chan, cmd_trig, cmd_mpl]
    for group in interfaces:
        for cmd in config:
            group.add_command(cmd)

    # plugin commands
    for group in interfaces:
        for plug in g_plugins_default:
            if plug.command:
                group.add_command(plug.command)
            else:  # pragma: no cover
                logger.error(
                    "no command implementation for plugin %s", plug.name
                )


# final click initialization
click_final_init()
