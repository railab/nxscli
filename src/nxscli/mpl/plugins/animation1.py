"""Module containing animation1 plugin."""

from typing import TYPE_CHECKING, Any

import click

from nxscli.main.environment import Environment, pass_environment
from nxscli.main.types import plot_options
from nxscli.mpl.animation_mpl import IPluginAnimation
from nxscli.mpl.plot_mpl import PlotDataAxesMpl, PluginAnimationCommonMpl

if TYPE_CHECKING:
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib.lines import Line2D  # type: ignore

    from nxscli.idata import PluginQueueData
    from nxscli.trigger import DTriggerConfigReq

###############################################################################
# Command: cmd_pani1
###############################################################################


@click.command(name="pani1")
@plot_options
@pass_environment
def cmd_pani1(
    ctx: Environment,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    dpi: float,
    fmt: list[list[str]],
    write: str,
) -> bool:
    """[plugin] Animation plot without a length limit (infinite plot)."""
    assert ctx.phandler
    ctx.phandler.enable(
        "animation1", channels=chan, trig=trig, dpi=dpi, fmt=fmt, write=write
    )

    ctx.needchannels = True

    return True


###############################################################################
# Class: Animation1
###############################################################################


class Animation1(PluginAnimationCommonMpl):
    """Infinity animation with x axis extension."""

    def __init__(
        self,
        fig: "Figure",
        pdata: PlotDataAxesMpl,
        qdata: "PluginQueueData",
        write: str,
    ) -> None:
        """Initialzie an animtaion1 handler.

        :param fig: matplotlib Figure
        :param pdata: axes handler
        :param qdata: stream queue handler
        :param write: write path
        """
        PluginAnimationCommonMpl.__init__(self, fig, pdata, qdata, write)

    def _animation_update(
        self, frame: tuple[list[Any], list[Any]], pdata: PlotDataAxesMpl
    ) -> "Line2D":  # pragma: no cover
        """Update an animation with dynamic scaling."""
        # update sample
        pdata.xdata_extend(frame[0])
        pdata.ydata_extend(frame[1])

        # update y scale
        self.yscale_extend(frame[1], pdata)

        # update x scale
        self.xscale_extend(frame[0], pdata)

        # set new data
        i = 0
        for ln in pdata.lns:
            ln.set_data(pdata.xdata[i], pdata.ydata[i])
            i += 1

        return pdata.lns


###############################################################################
# Class: PluginAnimation1
###############################################################################


class PluginAnimation1(IPluginAnimation):
    """Infinity animation with x axis extension."""

    def __init__(self) -> None:
        """Initialize an animation1 plugin."""
        IPluginAnimation.__init__(self)

    def _start(
        self,
        fig: "Figure",
        pdata: PlotDataAxesMpl,
        qdata: "PluginQueueData",
        kwargs: Any,
    ) -> PluginAnimationCommonMpl:
        """Start an animation1 plugin."""
        return Animation1(fig, pdata, qdata, kwargs["write"])
