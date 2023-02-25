"""Module containint the dummy interface command for CLI."""

import click
from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_dummy
###############################################################################


@click.group(name="dummy", chain=True)
@click.option("--writepadding", default=0)
@click.option(
    "--streamsleep", type=float, default=0.001, help="dummy dev parameter"
)
@click.option(
    "--samplesnum", type=int, default=100, help="dummy dev parameter"
)
@pass_environment
def cmd_dummy(
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
