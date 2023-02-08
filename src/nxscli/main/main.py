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

from nxscli.iplugin import EPluginType, IPlugin
from nxscli.logger import logger
from nxscli.pdefault import g_plugins_default
from nxscli.phandler import PluginHandler
from nxscli.plot_mpl import MplManager


@dataclass
class EnvironmentData:
    """Environment data."""

    debug: bool = False
    waitenter: bool = False
    nxscope: NxscopeHandler | None = None
    parser: Parser | None = None
    plugins: list | None = None
    interface: bool = False
    needchannels: bool = False
    channels: tuple | None = None
    phandler: PluginHandler | None = None


class Environment(EnvironmentData):
    """A class with application environmet."""

    _testctx = False

    def __init__(self) -> None:
        """Initialize environmet."""
        super().__init__()

    @property
    def testctx(self) -> bool:
        """Return True if we are in the test context."""
        return self._testctx

    @classmethod
    def testctx_set(cls: type["Environment"], val: bool) -> None:
        """Set the test context - workaroud for a plugins busy-waiting."""
        cls._testctx = val


# custom environmet decorator
pass_environment = click.make_pass_decorator(Environment, ensure=True)


@click.group()
@click.option(
    "--debug/--no-debug", default=False, is_flag=True, envvar="NXSCLI_DEBUG"
)
@pass_environment
def main(ctx: Any, debug: bool) -> bool:
    """Nxscli - CLI to the Nxslib."""
    ctx.debug = debug
    if debug:  # pragma: no cover
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

    # configure mplt
    MplManager.mpl_config()

    ctx.phandler = PluginHandler(g_plugins_default)
    ctx.nxscope = NxscopeHandler()
    parse = Parser()
    ctx.parser = parse
    ctx.plugins = []

    click.get_current_context().call_on_close(cli_on_close)

    return True


@main.group(chain=True)
@click.option("--writepadding", default=0)
@pass_environment
def dummy(ctx: Environment, writepadding: int) -> bool:
    """[interface] use dummy interface."""
    assert ctx.phandler
    assert ctx.parser
    assert ctx.nxscope
    intf = DummyDev()
    intf.write_padding = writepadding

    # initialize nxslib communication handler
    comm = CommHandler(intf, ctx.parser)
    ctx.nxscope.intf_connect(comm)

    # connect nxscope to phandler
    ctx.phandler.nxscope_connect(ctx.nxscope)

    ctx.interface = True

    return True


@main.group(chain=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option("--baud", default=115200)
@click.option("--writepadding", default=0)
@pass_environment
def serial(
    ctx: Environment, path: str, baud: int, writepadding: bool
) -> bool:  # pragma: no cover
    """[interface] use serial port interface."""
    assert ctx.phandler
    assert ctx.nxscope
    assert ctx.parser
    intf = SerialDevice(path, baud=baud)
    intf.write_padding = writepadding

    # initialize nxslib communication handler
    comm = CommHandler(intf, ctx.parser)
    ctx.nxscope.intf_connect(comm)

    # connect nxscope to phandler
    ctx.phandler.nxscope_connect(ctx.nxscope)

    ctx.interface = True

    return True


class Channels(click.ParamType):
    """Parse channels argument."""

    name = "channels"

    def convert(self, value: Any, param: Any, ctx: Any) -> list[int]:
        """Convert channels argument."""
        lint = []
        if value == "all":
            # special case to indicate all channels
            lint.append(-1)
            return lint

        lstr = value.split(",")
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

    def convert(self, value: Any, param: Any, ctx: Any) -> list[int]:
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
def chan(ctx: Environment, channels: list[int], divider: Any) -> bool:
    """[config] Channels configuration.

    This command configure and enable channels.
    By default all channels from this command are passed to the plugins,
    but can be precisely selected with plugin '--channels' option.
    """
    assert ctx.phandler
    ctx.channels = (channels, divider)
    # configure channles
    ctx.phandler.channels_configure(channels, divider)

    return True


_channels_option_help = "plugin specific channels configuration"
# common plot options
_plot_options = (
    click.option(
        "--chan",
        default=None,
        type=Channels(),
        help=_channels_option_help,
    ),
    click.option("--dpi", type=int, default=100),
    click.option("--fmt", default=""),
    click.option("--write", type=click.Path(resolve_path=False), default=None),
)


def plot_options(fn: Any) -> Any:
    """Decorate command with common plot options decorator."""
    for decorator in reversed(_plot_options):
        fn = decorator(fn)
    return fn


@click.command()
@plot_options
@pass_environment
def pani1(
    ctx: Environment, chan: list[int], dpi: float, fmt: str, write: str | None
) -> bool:
    """[plugin] dynamic animation without length limit."""
    assert ctx.phandler
    ctx.phandler.enable(
        "animation1", channels=chan, dpi=dpi, fmt=fmt, write=write
    )

    ctx.needchannels = True

    return True


@click.command()
@click.argument("maxsamples", type=int, required=True)
@plot_options
@pass_environment
def pani2(
    ctx: Environment,
    maxsamples: int,
    chan: list[int],
    dpi: float,
    fmt: str,
    write: str | None,
) -> bool:
    """[plugin] dynamic animation with length limit."""
    assert ctx.phandler
    if maxsamples == 0:  # pragma: no cover
        click.secho("ERROR: Missing argument MAXSAMPLES", err=True, fg="red")
        return False

    ctx.phandler.enable(
        "animation2",
        maxsamples=maxsamples,
        channels=chan,
        dpi=dpi,
        fmt=fmt,
        write=write,
    )

    ctx.needchannels = True

    return True


@click.command()
@click.argument("samples", type=int, required=True)
@plot_options
@pass_environment
def pcap(
    ctx: Environment,
    samples: int,
    chan: list[int],
    dpi: float,
    fmt: str,
    write: str | None,
) -> bool:
    """[plugin] capture static plot.

    If SAMPLES argument is set to 0 then we capture data until enter is press.
    """
    # wait for enter if samples set to 0
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "capture",
        samples=samples,
        channels=chan,
        dpi=dpi,
        fmt=fmt,
        write=write,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

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
def pcsv(
    ctx: Environment, samples: int, path: str, chan: list[int], metastr: bool
) -> bool:
    """[plugin] Store samples in csv files.

    If SAMPLES argument is set to 0 then we capture data until enter is press.
    Each channel will be stored in a separate file.
    """
    # wait for enter if samples set to 0
    assert ctx.phandler
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

    ctx.needchannels = True

    return True


@click.command()
@pass_environment
def pdevinfo(ctx: Environment) -> bool:
    """[plugin] Show NxSope device info."""
    assert ctx.phandler
    ctx.phandler.enable("devinfo")

    return True


def devinfo_print(info: dict) -> None:
    """Print device information."""
    print("\nDevice common:\n")
    pprint.pprint(info["cmn"])
    print("\nDevice channels:")
    pprint.pprint(info["channels"])
    print("\n")


def handle_plugin(plugin: type[IPlugin]) -> tuple | None:
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


def plugin_loop(ctx: Environment) -> list:
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
                if ret is not None:
                    ret.append(r)
                else:  # pragma: no cover
                    pass
        else:  # pragma: no cover
            pass

    return ret


def wait_for_plugins(ret: list) -> None:
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
def cli_on_close(ctx: Environment) -> bool:
    """Handle requested plugins on Click close."""
    assert ctx.phandler
    assert ctx.nxscope
    if ctx.interface is False:
        return False

    if ctx.needchannels and ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        return False

    if len(ctx.phandler.enabled) == 0:
        click.secho("ERROR: No plugins selected !", err=True, fg="red")
        ctx.nxscope.disconnect()
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
    ctx.nxscope.disconnect()

    return True


def click_final_init() -> None:
    """Handle final Click initialization."""
    commands = [chan, pani1, pani2, pcap, pcsv, pdevinfo]
    groups = [dummy, serial]

    # add commands to interfaces
    for group in groups:
        for cmd in commands:
            group.add_command(cmd)


# final click initialization
click_final_init()
