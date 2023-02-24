"""The matplotlib plot specific command."""

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import StringList
from nxscli.mpl.plot_mpl import MplManager

###############################################################################
# Command: cmd_mpl
###############################################################################


@click.command(name="mpl")
@click.option(
    "--style",
    default="ggplot,fast",
    type=StringList(),
    help="Configure Matplotlib style, default: ggplot, fast",
)
@pass_environment
def cmd_mpl(ctx: Environment, style: list[str]) -> bool:
    """[config] Matplotlib configuration."""  # noqa: D301
    MplManager.style_set(style)
    return True


# default configuration
MplManager.style_set(["ggplot", "fast"])
