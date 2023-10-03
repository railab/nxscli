"""Module containing UDP plugin command."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Command: cmd_pudp
###############################################################################


@click.command(name="pudp")
@click.argument("samples", type=Samples(), required=True)
@click.option(
    "--address",
    type=str,
    default="127.0.0.1",
    help="destinantion port. Default: 127.0.0.1",
)
@click.option(
    "--port", type=int, default=9870, help="destination port. Default: 9870"
)
@click.option(
    "--dataformat", type=str, default="json", help="Data format. Default: json"
)
@capture_options
@pass_environment
def cmd_pudp(
    ctx: Environment,
    samples: int,
    address: str,
    port: int,
    dataformat: str,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
) -> bool:
    """[plugin] Stream parsed data to UDP port.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.

    """  # noqa: D301
    # wait for enter if samples set to 'i'
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "udp",
        samples=samples,
        address=address,
        port=port,
        data_format=dataformat,
        channels=chan,
        trig=trig,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True
