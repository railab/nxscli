"""Module containint the interface command for CLI."""

import click
from nxslib.intf.dummy import DummyDev
from nxslib.intf.serial import SerialDevice
from nxslib.nxscope import NxscopeHandler

from nxscli.main.environment import Environment, pass_environment

###############################################################################
# Function: dummy
###############################################################################


@click.group(chain=True)
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


@click.group(chain=True)
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
