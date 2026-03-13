"""Module containint the UDP interface command for CLI."""

import click
from nxslib.intf.udp import UdpDevice
from nxslib.nxscope import NxscopeHandler

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_udp
###############################################################################


@click.group(name="udp", chain=True)
@click.argument("host", type=str, required=True)
@click.argument("port", type=int, required=True)
@click.option("--local-port", type=int, default=0, help="Default: 0")
@click.option("--writepadding", default=0, help="Default: 0")
@pass_environment
def cmd_udp(
    ctx: Environment,
    host: str,
    port: int,
    local_port: int,
    writepadding: int,
) -> bool:  # pragma: no cover
    """[interface] Connect with a UDP NxScope devie."""
    intf = UdpDevice(host, port, local_port=local_port)
    intf.write_padding = writepadding

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(
        intf, ctx.parser, enable_bitrate_tracking=True
    )

    ctx.interface = True

    return True
