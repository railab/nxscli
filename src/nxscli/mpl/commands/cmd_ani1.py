"""Module containing animation1 plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import plot_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pani1
###############################################################################


@click.command(name="pani1")
@plot_options
@pass_environment
def cmd_pani1(
    ctx: Environment,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Animation plot without a length limit (infinite plot)."""
    assert ctx.phandler
    ctx.phandler.enable(
        "animation1", channels=chan, trig=trig, dpi=dpi, fmt=fmt, write=write
    )

    ctx.needchannels = True

    return True
