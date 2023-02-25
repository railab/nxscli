"""Module containint the channels configuration command for CLI."""

from typing import Any

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Channels, Divider, divider_option_help

###############################################################################
# Command: cmd_chan
###############################################################################


@click.command(name="chan")
@click.argument("channels", required=True, type=Channels())
@click.option(
    "--divider", default="0", type=Divider(), help=divider_option_help
)
@pass_environment
def cmd_chan(ctx: Environment, channels: list[int], divider: Any) -> bool:
    """[config] Channels declaration and configuration.

    This command configure and enable given channels.
    The channels must be integer separated by commas, eg 'chan 1,2,3'.
    All availalbe channels can be configured with a single word 'all'.

    By default all channels from this command are passed to all plugins.

    \b
    You can precisesly configure the channels for a given plugin using
    the '--chan' option.
    """  # noqa: D301
    ctx.channels = (channels, divider)

    return True
