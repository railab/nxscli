"""Module containing captgure plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, plot_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pcap
###############################################################################


@click.command(name="pcap")
@click.argument("samples", type=Samples(), required=True)
@plot_options
@pass_environment
def cmd_pcap(
    ctx: Environment,
    samples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Static plot for a given number of samples.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
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
