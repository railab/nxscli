"""Module containing devinfo plugin command."""

import click

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_pdevinfo
###############################################################################


@click.command(name="pdevinfo")
@pass_environment
def cmd_pdevinfo(ctx: Environment) -> bool:
    """[plugin] Show information about the connected NxScope device."""
    assert ctx.phandler
    ctx.phandler.enable("devinfo")

    return True
