"""Module containing Numpy capture plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pnpsave
###############################################################################


@click.command(name="pnpsave")
@click.argument("samples", type=Samples(), required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@capture_options
@pass_environment
def cmd_pnpsave(
    ctx: Environment,
    samples: int,
    path: str,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
) -> bool:
    """[plugin] Store samples in Numpy files.

    Each configured channel will be stored in a separate file.
    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
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
