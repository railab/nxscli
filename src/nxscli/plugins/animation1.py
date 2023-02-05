"""Module containing animation1 plugin."""

from nxscli.animation_mpl import IPluginAnimation
from nxscli.idata import PluginQueueData
from nxscli.plot_mpl import PlotDataAxesMpl, PluginAnimationCommonMpl

###############################################################################
# Class: Animation1
###############################################################################


class Animation1(PluginAnimationCommonMpl):
    """Infinity animation with x axis extension."""

    def __init__(self, fig, pdata, qdata, write):
        """Initialzie an animtaion1 handler."""
        PluginAnimationCommonMpl.__init__(self, fig, pdata, qdata, write)

    def _animation_update(self, frame, pdata):  # pragma: no cover
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

    def __init__(self):
        """Initialize an animation1 plugin."""
        IPluginAnimation.__init__(self)

    def _start(
        self, fig, pdata: PlotDataAxesMpl, qdata: PluginQueueData, kwargs
    ) -> PluginAnimationCommonMpl:
        """Start an animation1 plugin."""
        return Animation1(fig, pdata, qdata, kwargs["write"])
