"""Module containing Numpy memmap plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pnpmem
###############################################################################


@click.command(name="pnpmem")
@click.argument("samples", type=Samples(), required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.argument("shape", type=int, required=True)
@capture_options
@pass_environment
def cmd_pnpmem(
    ctx: Environment,
    samples: int,
    path: str,
    shape: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
) -> bool:
    """[plugin] Store samples in Numpy memmap files.

    Each configured channel will be written to a separate file.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.

    The 'shape' argument defines the second dimension of the memmap array.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "npmem",
        samples=samples,
        path=path,
        channels=chan,
        shape=shape,
        trig=trig,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True
