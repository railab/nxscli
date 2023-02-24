"""Module containing animation2 plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import plot_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pani2
###############################################################################


@click.command(name="pani2")
@click.argument("maxsamples", type=int, required=True)
@plot_options
@pass_environment
def cmd_pani2(
    ctx: Environment,
    maxsamples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Animation plot with a lenght limit (saturated X-axis)."""
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
