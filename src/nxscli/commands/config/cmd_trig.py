"""Module containint the trigger configuration commnad for CLI."""

from typing import TYPE_CHECKING

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Trigger

if TYPE_CHECKING:
    from nxscli.trigger import DTriggerConfigReq


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
       we - window enter, parameters: [hoffset, low, high]
       wx - window exit, parameters: [hoffset, low, high]

    Optional named trigger options:
       mode=start_after|stop_after
       pre=<samples>
       post=<samples>
       holdoff=<samples>
       rearm=true|false

    \b
    where:
       hoffset - legacy pre-trigger sample count
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
    - all chans stream until edge, then keep 64 post-trigger samples:
      'g:er,0,0.5,mode=stop_after,post=64'
    - all chans capture 32 samples before rising edge:
      'g:er,0,0.5,pre=32'
    - all chans capture 32 samples before entering window [-0.5, 0.5]:
      'g:we,0,-0.5,0.5,pre=32'
    - all chans capture after exiting window [-0.25, 0.25]:
      'g:wx,0,-0.25,0.25'
    """  # noqa: D301
    assert ctx.phandler
    ctx.triggers = triggers
    # configure triggers
    ctx.phandler.triggers_configure(ctx.triggers)

    return True
