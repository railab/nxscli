"""Module containint the CLI logic for Nxslib."""

import pprint
import sys
from typing import TYPE_CHECKING, Any

import click
from nxslib.intf.dummy import DummyDev
from nxslib.intf.serial import SerialDevice
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.iplugin import EPluginType, IPlugin
from nxscli.logger import logger
from nxscli.main.environment import Environment, pass_environment
from nxscli.main.types import (
    Channels,
    Divider,
    StringList,
    Trigger,
    divider_option_help,
)
from nxscli.pdefault import g_plugins_default
from nxscli.phandler import PluginHandler
from nxscli.plot_mpl import MplManager

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


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
# Function: dummy
###############################################################################


@main.group(chain=True)
@click.option("--writepadding", default=0)
@click.option(
    "--streamsleep", type=float, default=0.001, help="dummy dev parameter"
)
@click.option(
    "--samplesnum", type=int, default=100, help="dummy dev parameter"
)
@pass_environment
def dummy(
    ctx: Environment, writepadding: int, streamsleep: float, samplesnum: int
) -> bool:
    """[interface] Connect with a simulated NxScope devicve.

    \b
    Channels data:
      chan0 - vdim = 1, random()
      chan1 - vdim = 1, saw wave
      chan2 - vdim = 1, triangle wave
      chan3 - vdim = 2, random()
      chan4 - vdim = 3, random()
      chan5 - vdim = 3, static vector = [1.0, 0.0, -1.0]
      chan6 - vdim = 1, 'hello' string
      chan7 - vdim = 3, static vector = [1.0, 0.0, -1.0], meta = 1B int
      chan8 - vdim = 0, meta = 'hello string', mlen = 16
      chan9 - vdim = 3, 3-phase sine wave
    """  # noqa: D301
    intf = DummyDev(
        rxpadding=writepadding,
        stream_sleep=streamsleep,
        stream_snum=samplesnum,
    )

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(intf, ctx.parser)

    ctx.interface = True

    return True


###############################################################################
# Function: serial
###############################################################################


@main.group(chain=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option("--baud", default=115200)
@click.option("--writepadding", default=0)
@pass_environment
def serial(
    ctx: Environment, path: str, baud: int, writepadding: bool
) -> bool:  # pragma: no cover
    """[interface] Connect with a serial port NxScope devie."""
    intf = SerialDevice(path, baud=baud)
    intf.write_padding = writepadding

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(intf, ctx.parser)

    ctx.interface = True

    return True


###############################################################################
# Function: mpl
###############################################################################


@click.command()
@click.option(
    "--style",
    default="ggplot,fast",
    type=StringList(),
    help="Configure Matplotlib style, default: ggplot, fast",
)
@pass_environment
def mpl(ctx: Environment, style: list[str]) -> bool:
    """[config] Matplotlib configuration."""  # noqa: D301
    ctx.mplstyle = style

    return True


###############################################################################
# Function: chan
###############################################################################


@click.command()
@click.argument("channels", required=True, type=Channels())
@click.option(
    "--divider", default="0", type=Divider(), help=divider_option_help
)
@pass_environment
def chan(ctx: Environment, channels: list[int], divider: Any) -> bool:
    """[config] Channels declaration and configuration.

    This command configure and enable given channels.
    The channels must be integer separated by commas, eg 'chan 1,2,3'.
    All availalbe channels can be configured with a single word 'all'.

    By default all channels from this command are passed to all plugins.

    \b
    You can precisesly configure the channels for a given plugin using
    the '--chan' option.
    """  # noqa: D301
    ctx.channels = (channels, divider)

    return True


###############################################################################
# Function: trig
###############################################################################


@click.command()
@click.argument("triggers", type=Trigger())
@pass_environment
def trig(ctx: Environment, triggers: dict[int, "DTriggerConfigReq"]) -> bool:
    """[config] Triggers configuration.

    This command configure software triggers.

    Format: '[channel]:[trigger][#chan_source][@chan_vector][parameters]'

    You can define many triggers at once, just separate them with
    a semicolon (;). The configuration request must be surrounded
    by quotation marks. All spaces are ignored.

    If channel is equal to character 'g' then the trigger is considered
    global for all channels.

    You can precisesly configure the triggers for a given plugin using
    the '--trig' option.

    \b
    Supported 'trigger' options:
       on - always on
       off - always off
       er - edge rising, parameters: [hoffset, level]
       ef - edge falling: [hoffset, level]

    \b
    where:
       hoffset - horizontal offset for triggered data
       level - trigger level

    Default: all channels on ('g:on').

    \b
    Some triggers configuration examples:
    - all chans triggered on a rising edge, hoffset=0, level=10.0:
      'g:er,0,10.0'
    - all chans triggered on a chan 0 rising edge, hoffset=0, level=10.0:
      'g:er#0,0,10.0'
    - chan 1 triggered on a vect 3 rising edge, hoffset=0, level=10.0:
      '1:er@3,0,10.0'
    - chan 2 triggered on chan 3 falling edge, hoffset=10, level=-10:
      '2:er#2,10,-10'
    - chan 2 triggered on chan 3 vect 1 falling edge, hoffset=0, level=1,
      chan 3 always on,
      chan 4 always off,
      white spaces ignored:
      '2 : er#2@1, 0, 1; 3 : on; 4 : off'
    """  # noqa: D301
    assert ctx.phandler
    ctx.triggers = triggers
    # configure triggers
    ctx.phandler.triggers_configure(ctx.triggers)

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
    commands = [chan, trig, mpl]
    for plug in g_plugins_default:
        if plug.command:
            commands.append(plug.command)
        else:  # pragma: no cover
            logger.error("no command implementation for plugin %s", plug.name)

    groups = [dummy, serial]

    # add commands to interfaces
    for group in groups:
        for cmd in commands:
            group.add_command(cmd)


# final click initialization
click_final_init()
