"""Module containing animation1 plugin."""

from typing import TYPE_CHECKING

from nxscli.animation_mpl import IPluginAnimation
from nxscli.plot_mpl import PlotDataAxesMpl, PluginAnimationCommonMpl

if TYPE_CHECKING:
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib.lines import Line2D  # type: ignore

    from nxscli.idata import PluginQueueData

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
        self, frame: list, pdata: PlotDataAxesMpl
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
        kwargs: dict,
    ) -> PluginAnimationCommonMpl:
        """Start an animation1 plugin."""
        return Animation1(fig, pdata, qdata, kwargs["write"])
