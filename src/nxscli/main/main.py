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

###############################################################################
# Class: DEnvironmentData
###############################################################################


@dataclass
class DEnvironmentData:
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
    triggers: dict | None = None


###############################################################################
# Class: Environment
###############################################################################


class Environment(DEnvironmentData):
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


###############################################################################
# Class: Channels
###############################################################################


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


###############################################################################
# Class: Trigger
###############################################################################


class Trigger(click.ParamType):
    """Parse trigger argument."""

    name = "trigger"

    req_split = ";"
    req_assign = "="
    req_separator = ","
    req_chan = "!"
    req_global = "g"

    def convert(self, value: Any, param: Any, ctx: Any) -> dict:
        """Convert trigger argument."""
        # remove white spaces
        tmp = value.strip()
        # split requests
        tmp = tmp.split(self.req_split)
        # get configurations
        ret = {}
        for trg in tmp:
            chan, params = trg.split(self.req_assign)
            tmp = params.split(self.req_separator)

            cfg = []
            if "!" in tmp[0]:  # pragma: no cover
                cfg.append(tuple(tmp[0].split(self.req_chan)))
            else:
                cfg.append((tmp[0], None))

            cfg += tmp[1:]
            if chan == self.req_global:
                chan = -1
            ret[int(chan)] = cfg
        return ret


###############################################################################
# Class: Divider
###############################################################################


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


###############################################################################
# Decorator: plot_options
###############################################################################


_channels_option_help = "plugin specific channels configuration"
_trigger_option_help = "plugin specific triggers configuration"
# common plot options
_plot_options = (
    click.option(
        "--chan",
        default=None,
        type=Channels(),
        help=_channels_option_help,
    ),
    click.option(
        "--trig",
        default=None,
        type=Trigger(),
        help=_trigger_option_help,
    ),
    click.option("--dpi", type=int, default=100),
    click.option("--fmt", default=""),
    click.option("--write", type=click.Path(resolve_path=False), default=""),
)


def plot_options(fn: Any) -> Any:
    """Decorate command with common plot options decorator."""
    for decorator in reversed(_plot_options):
        fn = decorator(fn)
    return fn


###############################################################################
# Decorator: pass_environment
###############################################################################


# custom environmet decorator
pass_environment = click.make_pass_decorator(Environment, ensure=True)


###############################################################################
# Function: main
###############################################################################


@click.group()
@click.option(
    "--debug/--no-debug", default=False, is_flag=True, envvar="NXSCLI_DEBUG"
)
@pass_environment
def main(ctx: Environment, debug: bool) -> bool:
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
    ctx.triggers = {}

    click.get_current_context().call_on_close(cli_on_close)

    return True


###############################################################################
# Function: dummy
###############################################################################


@main.group(chain=True)
@click.option("--writepadding", default=0)
@pass_environment
def dummy(ctx: Environment, writepadding: int) -> bool:
    r"""[interface] Connect with a simulated NxScope devicve.

    Channels data:
      chan0 - vdim = 1, random()
      chan1 - vdim = 1, saw
      chan2 - vdim = 1, triangle
      chan3 - vdim = 2, random()
      chan4 - vdim = 3, random()
      chan5 - vdim = 3, static vector = [1.0, 0.0, -1.0]
      chan6 - vdim = 1, 'hello' string
      chan7 - vdim = 3, static vector = [1.0, 0.0, -1.0], meta = 1B int
      chan7 - vdim = 0, meta = 'hello string', mlen = 16
    """
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


###############################################################################
# Function: chan
###############################################################################


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


###############################################################################
# Function: trig
###############################################################################


@click.command()
@click.argument("triggers", type=Trigger())
@pass_environment
def trig(ctx: Environment, triggers: dict) -> bool:
    """[config] Triggers configuration.

    This command configure software tirggers.

    Format: [channel]=[trigger][parameters]
    Default: all channels on
    """
    assert ctx.phandler
    ctx.triggers = triggers
    # configure triggers
    ctx.phandler.triggers_configure(ctx.triggers)

    return True


###############################################################################
# Function: pani1
###############################################################################


@click.command()
@plot_options
@pass_environment
def pani1(
    ctx: Environment,
    chan: list[int],
    trig: dict,
    dpi: float,
    fmt: str,
    write: str,
) -> bool:
    """[plugin] Animation plot without a length limit."""
    assert ctx.phandler
    ctx.phandler.enable(
        "animation1", channels=chan, trig=trig, dpi=dpi, fmt=fmt, write=write
    )

    ctx.needchannels = True

    return True


###############################################################################
# Function: pani2
###############################################################################


@click.command()
@click.argument("maxsamples", type=int, required=True)
@plot_options
@pass_environment
def pani2(
    ctx: Environment,
    maxsamples: int,
    chan: list[int],
    trig: dict,
    dpi: float,
    fmt: str,
    write: str,
) -> bool:
    """[plugin] Animation plot with a lenght limit."""
    assert ctx.phandler
    if maxsamples == 0:  # pragma: no cover
        click.secho("ERROR: Missing argument MAXSAMPLES", err=True, fg="red")
        return False

    ctx.phandler.enable(
        "animation2",
        maxsamples=maxsamples,
        channels=chan,
        trig=trig,
        dpi=dpi,
        fmt=fmt,
        write=write,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Function: pcap
###############################################################################


@click.command()
@click.argument("samples", type=int, required=True)
@plot_options
@pass_environment
def pcap(
    ctx: Environment,
    samples: int,
    chan: list[int],
    trig: dict,
    dpi: float,
    fmt: str,
    write: str,
) -> bool:
    """[plugin] Static plot for a given number of samples.

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
        trig=trig,
        dpi=dpi,
        fmt=fmt,
        write=write,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Function: pcsv
###############################################################################


@click.command()
@click.argument("samples", type=int, required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option(
    "--chan", default=None, type=Channels(), help=_channels_option_help
)
@click.option(
    "--trig", default=None, type=Trigger(), help=_trigger_option_help
)
@click.option(
    "--metastr", default=False, is_flag=True, help="store metadata as string"
)
@pass_environment
def pcsv(
    ctx: Environment,
    samples: int,
    path: str,
    chan: list[int],
    trig: dict,
    metastr: bool,
) -> bool:
    """[plugin] Store samples in CSV files.

    Each configured channel will be stored in a separate file.
    If SAMPLES argument is set to 0 then we capture data until enter is press.
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
        trig=trig,
        metastr=metastr,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Function: pnpsave
###############################################################################


@click.command()
@click.argument("samples", type=int, required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option(
    "--chan", default=None, type=Channels(), help=_channels_option_help
)
@click.option(
    "--trig", default=None, type=Trigger(), help=_trigger_option_help
)
@pass_environment
def pnpsave(
    ctx: Environment, samples: int, path: str, chan: list[int], trig: dict
) -> bool:
    """[plugin] Store samples in Nump files.

    Each configured channel will be stored in a separate file.
    If SAMPLES argument is set to 0 then we capture data until enter is press.
    """
    # wait for enter if samples set to 0
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "npsave",
        samples=samples,
        path=path,
        channels=chan,
        trig=trig,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Function: pdevinfo
###############################################################################


@click.command()
@pass_environment
def pdevinfo(ctx: Environment) -> bool:
    """[plugin] Show NxSope device info."""
    assert ctx.phandler
    ctx.phandler.enable("devinfo")

    return True


###############################################################################
# Function: devinfo_print
###############################################################################


def devinfo_print(info: dict) -> None:
    """Print device information."""
    print("\nDevice common:\n")
    pprint.pprint(info["cmn"])
    print("\nDevice channels:")
    pprint.pprint(info["channels"])
    print("\n")


###############################################################################
# Function: handle_plugin
###############################################################################


def handle_plugin(plugin: type[IPlugin]) -> tuple:
    """Handle a given plugin."""
    if plugin.ptype is EPluginType.TEXT:
        # REVISIT: only devinfo supported for now
        info = plugin.result()
        devinfo_print(info)
        return ()

    elif plugin.ptype is EPluginType.PLOT:
        plot = plugin.result()
        for pdata in plot.plist:
            # plot samples
            pdata.plot()
        MplManager.show(block=False)
        return (EPluginType.PLOT, plot)

    elif plugin.ptype is EPluginType.ANIMATION:
        plot = plugin.result()
        MplManager.show(block=False)
        return (EPluginType.ANIMATION, plot)

    elif plugin.ptype is EPluginType.FILE:
        print("TODO: file handler ?")
        return ()

    else:
        raise AssertionError


###############################################################################
# Function: plugin_loop
###############################################################################


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
                if ret:  # pragma: no cover
                    ret.append(r)
        else:  # pragma: no cover
            pass

    return ret


###############################################################################
# Function: wait_for_plugins
###############################################################################


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


###############################################################################
# Function: cli_on_close
###############################################################################


@pass_environment
def cli_on_close(ctx: Environment) -> bool:
    """Handle requested plugins on Click close."""
    assert ctx.phandler
    assert ctx.nxscope
    if ctx.interface is False:
        return False

    if ctx.needchannels and ctx.channels is None:  # pragma: no cover
        click.secho("ERROR: No channels selected !", err=True, fg="red")
        ctx.nxscope.disconnect()
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


###############################################################################
# Function: click_final_init
###############################################################################


def click_final_init() -> None:
    """Handle final Click initialization."""
    commands = [chan, trig, pani1, pani2, pcap, pcsv, pnpsave, pdevinfo]
    groups = [dummy, serial]

    # add commands to interfaces
    for group in groups:
        for cmd in commands:
            group.add_command(cmd)


# final click initialization
click_final_init()
