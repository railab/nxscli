"""Module containing animation2 plugin."""

from nxscli.animation_mpl import IPluginAnimation
from nxscli.idata import PluginQueueData
from nxscli.plot_mpl import PlotDataAxesMpl, PluginAnimationCommonMpl

###############################################################################
# Class: Animation2
###############################################################################


class Animation2(PluginAnimationCommonMpl):
    """Animation with x axis saturation."""

    def __init__(
        self, fig, pdata, qdata, write, static_xticks=True, disable_xaxis=False
    ):
        """Initialzie an animtaion2 handler."""
        PluginAnimationCommonMpl.__init__(self, fig, pdata, qdata, write)

        if static_xticks is True:
            self._animation_update = self._animation_update_staticx
        else:  # pragma: no cover
            self._animation_update = self._animation_update_dynamicx

        if disable_xaxis is True:  # pragma: no cover
            self.xaxis_disable()

    def _animation_update_staticx(self, frame, pdata):  # pragma: no cover
        """Update an animation with static X ticks."""
        # update sample
        pdata.xdata_extend_max(frame[0])
        pdata.ydata_extend_max(frame[1])

        # update y scale
        self.yscale_extend(frame[1], pdata)

        xdata = range(0, len(pdata.ydata[0]))
        i = 0
        for ln in pdata.lns:
            ln.set_data(xdata, pdata.ydata[i])
            i += 1

        return pdata.lns

    def _animation_update_dynamicx(self, frame, pdata):  # pragma: no cover
        """Update an animation with dynamic X ticks."""
        xdata = frame[0]
        ydata = frame[1]

        if not xdata or not ydata:
            return pdata.lns

        # update sample
        pdata.xdata_extend_max(xdata)
        pdata.ydata_extend_max(ydata)

        # update y scale
        self.yscale_extend(ydata, pdata)

        # update x scale
        self.xscale_saturate(xdata, pdata)

        # set new data
        i = 0
        for ln in pdata.lns:
            ln.set_data(pdata.xdata[i], pdata.ydata[i])
            i += 1

        return pdata.lns


###############################################################################
# Class: PluginAnimation2
###############################################################################


class PluginAnimation2(IPluginAnimation):
    """Animation with x axis saturation."""

    def __init__(self):
        """Initialize an animation2 plugin."""
        IPluginAnimation.__init__(self)

    def _start(
        self, fig, pdata: PlotDataAxesMpl, qdata: PluginQueueData, kwargs
    ) -> PluginAnimationCommonMpl:
        """Start an animation2 plugin."""
        maxsamples = kwargs["maxsamples"]

        # configure the max number of samples
        pdata.samples_max = maxsamples
        pdata.set_xlim((0, maxsamples))

        # start animation
        return Animation2(
            fig,
            pdata,
            qdata,
            kwargs["write"],
            static_xticks=True,
            disable_xaxis=False,
        )
