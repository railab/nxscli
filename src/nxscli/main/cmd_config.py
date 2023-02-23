"""Module containint the config command for CLI."""

from typing import TYPE_CHECKING, Any

import click

from nxscli.main.environment import Environment, pass_environment
from nxscli.main.types import Channels, Divider, Trigger, divider_option_help

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


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


###############################################################################
# Command: cmd_trig
###############################################################################


@click.command(name="trig")
@click.argument("triggers", type=Trigger())
@pass_environment
def cmd_trig(
    ctx: Environment, triggers: dict[int, "DTriggerConfigReq"]
) -> bool:
    """[config] Triggers configuration.

    This command configure software triggers.

    Format: '[channel]:[trigger][#chan_source][@chan_vector][parameters]'

    You can define many triggers at once, just separate them with
    a semicolon (;). The configuration request must be surrounded
    by quotation marks. All spaces are ignored.

    If channel is equal to character 'g' then the trigger is considered
    global for all channels.

    You can precisesly configure the triggers for a given plugin using
    the '--trig' option.

    \b
    Supported 'trigger' options:
       on - always on
       off - always off
       er - edge rising, parameters: [hoffset, level]
       ef - edge falling: [hoffset, level]

    \b
    where:
       hoffset - horizontal offset for triggered data
       level - trigger level

    Default: all channels on ('g:on').

    \b
    Some triggers configuration examples:
    - all chans triggered on a rising edge, hoffset=0, level=10.0:
      'g:er,0,10.0'
    - all chans triggered on a chan 0 rising edge, hoffset=0, level=10.0:
      'g:er#0,0,10.0'
    - chan 1 triggered on a vect 3 rising edge, hoffset=0, level=10.0:
      '1:er@3,0,10.0'
    - chan 2 triggered on chan 3 falling edge, hoffset=10, level=-10:
      '2:er#2,10,-10'
    - chan 2 triggered on chan 3 vect 1 falling edge, hoffset=0, level=1,
      chan 3 always on,
      chan 4 always off,
      white spaces ignored:
      '2 : er#2@1, 0, 1; 3 : on; 4 : off'
    """  # noqa: D301
    assert ctx.phandler
    ctx.triggers = triggers
    # configure triggers
    ctx.phandler.triggers_configure(ctx.triggers)

    return True
