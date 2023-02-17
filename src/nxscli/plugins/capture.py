"""Module containing capture plugin."""

from typing import TYPE_CHECKING

from nxscli.iplugin import IPluginPlotStatic
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.idata import PluginQueueData
    from nxscli.plot_mpl import PluginPlotMpl


###############################################################################
# Class: PluginCapture
###############################################################################


class PluginCapture(PluginThread, IPluginPlotStatic):
    """Plugin that plot static captured data."""

    def __init__(self) -> None:
        """Intiialize a capture plot plugin."""
        IPluginPlotStatic.__init__(self)
        PluginThread.__init__(self)

        self._plot: "PluginPlotMpl"
        self._write: str

    def _init(self) -> None:
        assert self._phandler

    def _final(self) -> None:
        logger.info("plot capture DONE")

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        # store data
        ydata: list[list] = [[] for v in range(pdata.vdim)]
        for sample in data:
            for i in range(pdata.vdim):
                # TODO: metadata not supported for now
                ydata[i].append(sample.data[i])

        # extend ydata
        self._plot.plist[j].ydata_extend(ydata)
        # get data len
        self._datalen[j] = len(self._plot.plist[j].ydata[0])

    def start(self, kwargs: dict) -> bool:
        """Start capture plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._write = kwargs["write"]
        self._nostop = kwargs["nostop"]

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        self._plot = self._phandler.plot_handler(
            chanlist, trig, dpi=kwargs["dpi"], fmt=kwargs["fmt"]
        )

        if not self._plot.qdlist or not self._plot.plist:  # pragma: no cover
            return False

        for pdata in self._plot.plist:
            # update xlim to fit our data
            if self._samples:
                pdata.set_xlim((0, self._samples))
            else:  # pragma: no cover
                pass

        self.thread_start(self._plot)

        return True

    def result(self) -> "PluginPlotMpl":
        """Get capture plugin result."""
        assert self._plot

        if self._write:  # pragma: no cover
            for pdata in self._plot.plist:
                pdata.plot()
            self._plot.fig.savefig(self._write)

        return self._plot
