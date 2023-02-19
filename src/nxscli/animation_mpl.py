"""Module containing the common matplotlib animation plugin logic."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from nxscli.iplugin import IPluginPlotDynamic
from nxscli.logger import logger

if TYPE_CHECKING:
    from matplotlib.figure import Figure  # type: ignore

    from nxscli.idata import PluginQueueData
    from nxscli.plot_mpl import (
        PlotDataAxesMpl,
        PluginAnimationCommonMpl,
        PluginPlotMpl,
    )


###############################################################################
# Class: IPluginAnimation
###############################################################################


class IPluginAnimation(IPluginPlotDynamic):
    """The common logic for an animation plugin."""

    def __init__(self) -> None:
        """Initialize an animation plugin."""
        super().__init__()

        self._plot: "PluginPlotMpl"

    @abstractmethod
    def _start(
        self,
        fig: "Figure",
        pdata: "PlotDataAxesMpl",
        qdata: "PluginQueueData",
        kwargs: Any,
    ) -> "PluginAnimationCommonMpl":
        """Abstract method.

        :param fig: matplotlib Figure
        :param pdata: axes handler
        :param qdata: stream queue handler
        :param kwargs: implementation specific arguments
        """

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop all animations."""
        assert self._plot

        if len(self._plot.ani) > 0:
            for ani in self._plot.ani:
                ani.stop()

    def clear(self) -> None:
        """Clear all animations."""
        assert self._plot

        self._plot.ani_clear()

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """
        return True

    def start(self, kwargs: Any) -> bool:
        """Start animation plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start %s", str(kwargs))

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        self._plot = self._phandler.plot_handler(
            chanlist, trig, dpi=kwargs["dpi"], fmt=kwargs["fmt"]
        )
        assert self._plot

        # clear previous animations
        self.clear()

        # new animations
        for i, pdata in enumerate(self._plot.plist):
            ani = self._start(
                self._plot.fig, pdata, self._plot.qdlist[i], kwargs
            )
            self._plot.ani_append(ani)

        for ani in self._plot.ani:
            ani.start()

        return True

    def result(self) -> "PluginPlotMpl":
        """Get animation plugin result."""
        assert self._plot
        return self._plot
