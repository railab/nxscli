"""Module containing CSV plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pcsv
###############################################################################


@click.command(name="pcsv")
@click.argument("samples", type=Samples(), required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@capture_options
@click.option(
    "--metastr", default=False, is_flag=True, help="store metadata as string"
)
@pass_environment
def cmd_pcsv(
    ctx: Environment,
    samples: int,
    path: str,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    metastr: bool,
) -> bool:
    """[plugin] Store samples in CSV files.

    Each configured channel will be stored in a separate file.
    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
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
