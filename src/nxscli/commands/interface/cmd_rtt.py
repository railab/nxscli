"""Module containint the RTT interface command for CLI."""

import click
from nxslib.intf.rtt import RTTDevice
from nxslib.nxscope import NxscopeHandler

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_rtt
###############################################################################


@click.group(name="rtt", chain=True)
@click.argument("target", type=str, required=True)
@click.argument("index", type=int, required=True)
@click.argument("bufsize", type=int, required=True)
@click.option(
    "--jintf", type=str, default="swd", help="JLink interface: `swd` or `jtag`"
)
@click.option(
    "--blockaddr",
    type=str,
    default="auto",
    help="RTT block address as hex or `auto`. Can be found with J-Link tools.",
)
@pass_environment
def cmd_rtt(
    ctx: Environment,
    target: str,
    index: int,
    bufsize: int,
    jintf: str,
    blockaddr: str,
) -> bool:  # pragma: no cover
    """[interface] Connect with a RTT interface to the NxScope devie.

    \b
    target - JLINK target device string. Can be found with J-Link tools.
    index - RTT buffer index
    bufsize - RTT UP buffer size
    """  # noqa: D301
    intf = RTTDevice(target, index, bufsize, jintf, blockaddr)

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(intf, ctx.parser)

    ctx.interface = True

    return True
