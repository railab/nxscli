"""Module containint the CLI logic for Nxslib."""

import pprint
from dataclasses import dataclass
from typing import Any

import click
from nxslib.comm import CommHandler
from nxslib.intf.dummy import DummyDev
from nxslib.intf.serial import SerialDevice
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.iplugin import EPluginType
from nxscli.logger import logger
from nxscli.pdefault import g_plugins_default
from nxscli.phandler import PluginHandler
from nxscli.plot_mpl import MplManager


@dataclass
class EnvironmentData:
    """Environment data."""

    debug: bool
    waitenter: bool
    nxslib: NxscopeHandler | None
    parser: Parser | None
    plugins: list
    interface: bool
    channels: Any
    phandler: PluginHandler


class Environment(EnvironmentData):
    """A class with application environmet."""

    _testctx = False

    def __init__(self):
        """Initialize environmet."""
        super().__init__(False, False, None, None, [], False, None, None)

    @property
    def testctx(self) -> bool:
        """Return True if we are in the test context."""
        return self._testctx

    @classmethod
    def testctx_set(cls, val: bool):
        """Set the test context - workaroud for a plugins busy-waiting."""
        cls._testctx = val


# custom environmet decorator
pass_environment = click.make_pass_decorator(Environment, ensure=True)


@click.group()
@click.option(
    "--debug/--no-debug", default=False, is_flag=True, envvar="NXSLIB_DEBUG"
)
@pass_environment
def main(ctx, debug):
    """Nxslib - Python based client to the Apache NuttX Nxslib library."""
    ctx.debug = debug
    if debug:  # pragma: no cover
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

    # configure mplt
    MplManager.mpl_config()

    nxslib = NxscopeHandler()
    ctx.phandler = PluginHandler(g_plugins_default)
    ctx.nxslib = nxslib
    parse = Parser()
    ctx.parser = parse

    ctx.plugins = []
    ctx.interface = False
    ctx.channels = None

    click.get_current_context().call_on_close(cli_on_close)


@main.group(chain=True)
@click.option("--writepadding", default=0)
@pass_environment
def dummy(ctx, writepadding):
    """[interface] use dummy interface."""
    intf = DummyDev()
    intf.write_padding = writepadding

    # initialize nxslibunication handler
    comm = CommHandler(intf, ctx.parser)
    ctx.nxslib.intf_connect(comm)

    # connect nxscope to phandler
    ctx.phandler.nxscope_connect(ctx.nxslib)

    ctx.interface = True


@main.group(chain=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option("--baud", default=115200)
@click.option("--writepadding", default=0)
@pass_environment
def serial(ctx, path, baud, writepadding):  # pragma: no cover
    """[interface] use serial port interface."""
    intf = SerialDevice(path, baud=baud)
    intf.write_padding = writepadding

    # initialize nxslibunication handler
    comm = CommHandler(intf, ctx.parser)
    ctx.nxslib.intf_connect(comm)

    # connect nxscope to phandler
    ctx.phandler.nxscope_connect(ctx.nxslib)

    ctx.interface = True


class Channels(click.ParamType):
    """Parse channels argument."""

    name = "channels"

    def convert(self, value, param, ctx):
        """Convert channels argument."""
        if value == "all":
            return "all"

        lstr = value.split(",")
        lint = []
        for chan in lstr:
            chan = int(chan)
            if chan < 0 or chan > 255:
                raise click.BadParameter(
                    "channel id must be in range [0, 255]"
                )
            lint.append(chan)

        return lint


class Divider(click.ParamType):
    """Parse divider argument."""

    name = "divider"

    def convert(self, value, param, ctx):
        """Convert divider argument."""
        lstr = value.split(",")
        lint = []
        for div in lstr:
            div = int(div)
            if div < 0 or div > 255:
                raise click.BadParameter("divnel id must be in range [0, 255]")
            lint.append(div)

        # return as int if one element
        if len(lint) == 1:
            return lint[0]
        # else return list
        return lint


@click.command()
@click.argument("channels", required=True, type=Channels())
@click.option("--divider", default="0", type=Divider())
@pass_environment
def chan(ctx, channels, divider):
    """[config] Channels configuration.

    This command configure and enable channels.
    By default all channels from this command are passed to the plugins,
    but can be precisely selected with plugin '--channels' option.
    """
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    ctx.channels = (channels, divider)
    # configure channles
    ctx.phandler.channels_configure(channels, divider)


_channels_option_help = "plugin specific channels configuration"
# common plot options
_plot_options = (
    click.option(
        "--chan",
        default=None,
        type=Channels(),
        help=_channels_option_help,
    ),
    click.option("--fmt", default=""),
    click.option("--write", type=click.Path(resolve_path=False), default=None),
)


def plot_options(fn):
    """Decorate command with common plot options decorator."""
    for decorator in reversed(_plot_options):
        fn = decorator(fn)
    return fn


@click.command()
@plot_options
@pass_environment
def animation1(ctx, chan, fmt, write):
    """[plugin] dynamic animation without length limit."""
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    if ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        return False

    ctx.phandler.enable("animation1", channels=chan, fmt=fmt, write=write)

    return True


@click.command()
@click.argument("maxsamples", type=int, required=True)
@plot_options
@pass_environment
def animation2(ctx, maxsamples, chan, fmt, write):
    """[plugin] dynamic animation with length limit."""
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    if ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        return False

    if maxsamples == 0:  # pragma: no cover
        click.secho("ERROR: Missing argument MAXSAMPLES", err=True, fg="red")
        return False

    ctx.phandler.enable(
        "animation2",
        maxsamples=maxsamples,
        channels=chan,
        fmt=fmt,
        write=write,
    )

    return True


@click.command()
@click.argument("samples", type=int, required=True)
@plot_options
@pass_environment
def capture(ctx, samples, chan, fmt, write):
    """[plugin] capture static plot.

    If SAMPLES argument is set to 0 then we capture data until enter is press.
    """
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    if ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        return False

    # wait for enter if samples set to 0
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "capture",
        samples=samples,
        channels=chan,
        fmt=fmt,
        write=write,
        nostop=ctx.waitenter,
    )

    return True


@click.command()
@click.argument("samples", type=int, required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option(
    "--chan", default=None, type=Channels(), help=_channels_option_help
)
@click.option(
    "--metastr", default=False, is_flag=True, help="store metadata as string"
)
@pass_environment
def csv(ctx, samples, path, chan, metastr):
    """[plugin] Store samples in csv files.

    If SAMPLES argument is set to 0 then we capture data until enter is press.
    Each channel will be stored in a separate file.
    """
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    if ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        return False

    # wait for enter if samples set to 0
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "csv",
        samples=samples,
        path=path,
        channels=chan,
        metastr=metastr,
        nostop=ctx.waitenter,
    )

    return True


@click.command()
@pass_environment
def devinfo(ctx):
    """[plugin] Show NxSope device info."""
    if ctx.interface is False:  # pragma: no cover
        click.secho("ERROR: No interface selected !", err=True, fg="red")
        return False

    ctx.phandler.enable("devinfo")

    return True


def devinfo_print(info):
    """Print device information."""
    print("\nDevice common:\n")
    pprint.pprint(info["cmn"])
    print("\nDevice channels:")
    pprint.pprint(info["channels"])
    print('\n')


def handle_plugin(plugin):
    """Handle a given plugin."""
    if plugin.ptype is EPluginType.TEXT:
        # REVISIT: only devinfo supported for now
        info = plugin.result()
        devinfo_print(info)
        return None

    elif plugin.ptype is EPluginType.PLOT:
        plot = plugin.result()
        for pdata in plot.plist:
            # plot samples
            pdata.plot()
        MplManager.show(block=False)
        return EPluginType.PLOT, plot

    elif plugin.ptype is EPluginType.ANIMATION:
        plot = plugin.result()
        MplManager.show(block=False)
        return EPluginType.ANIMATION, plot

    elif plugin.ptype is EPluginType.FILE:
        print("TODO: file handler ?")
        return None

    else:
        raise AssertionError


def plugin_loop(ctx):
    """Plugin loop."""
    ret = []
    while True:
        plugins = ctx.phandler.poll()
        if plugins is None:
            break

        if len(plugins) > 0:
            for x in plugins:
                r = handle_plugin(x)
                if ret is not None:
                    ret.append(r)
                else:  # pragma: no cover
                    pass
        else:  # pragma: no cover
            pass

    return ret


def wait_for_plugins(ret):
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


@pass_environment
def cli_on_close(ctx):
    """Handle requested plugins on Click close."""
    if ctx.interface is False:
        return False

    if len(ctx.phandler.enabled) == 0:
        click.secho("ERROR: No plugins selected !", err=True, fg="red")
        ctx.nxslib.disconnect()
        return False

    # start plugins
    ctx.phandler.start()

    if ctx.waitenter:  # pragma: no cover
        _ = input("wait for Enter key...")

    # plugins loop
    ret = plugin_loop(ctx)

    # wait for plugins only if not test
    if not ctx.testctx:
        # wait until all figers closed
        wait_for_plugins(ret)

    print("closing...")
    ctx.phandler.stop()
    ctx.nxslib.disconnect()


def click_final_init():
    """Handle final Click initialization."""
    commands = [chan, animation1, animation2, capture, csv, devinfo]
    groups = [dummy, serial]

    # add commands to interfaces
    for group in groups:
        for cmd in commands:
            group.add_command(cmd)


# final click initialization
click_final_init()
