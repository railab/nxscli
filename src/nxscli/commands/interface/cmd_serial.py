"""Module containint the serial interface command for CLI."""

import click
from nxslib.intf.serial import SerialDevice
from nxslib.nxscope import NxscopeHandler

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_serial
###############################################################################


@click.group(name="serial", chain=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@click.option("--baud", default=115200)
@click.option("--writepadding", default=0)
@pass_environment
def cmd_serial(
    ctx: Environment, path: str, baud: int, writepadding: bool
) -> bool:  # pragma: no cover
    """[interface] Connect with a serial port NxScope devie."""
    intf = SerialDevice(path, baud=baud)
    intf.write_padding = writepadding

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(intf, ctx.parser)

    ctx.interface = True

    return True
