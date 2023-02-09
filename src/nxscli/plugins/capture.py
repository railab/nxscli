"""Module containing capture plugin."""

import threading
from typing import TYPE_CHECKING

from nxslib.thread import ThreadCommon

from nxscli.iplugin import IPluginPlotStatic
from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.plot_mpl import PluginPlotMpl


###############################################################################
# Class: PluginCapture
###############################################################################


class PluginCapture(IPluginPlotStatic, ThreadCommon):
    """Plugin that plot static captured data."""

    def __init__(self) -> None:
        """Intiialize a capture plot plugin."""
        IPluginPlotStatic.__init__(self)
        ThreadCommon.__init__(
            self, self._start_thread, self._thread_init, self._thread_final
        )

        self._samples: int
        self._plot: "PluginPlotMpl"
        self._write: str
        self._ready = threading.Event()
        self._nostop = False
        self._datalen: list[int] = []

    def _is_done(self, datalen: list[int]) -> bool:
        if not self._nostop:
            # check if capture done
            done = True
            for x in datalen:
                if x < self._samples:
                    done = False
        else:  # pragma: no cover
            done = False
        return done

    def _thread_init(self) -> None:
        assert self._phandler

        self._datalen = [0 for _ in range(len(self._plot.qdlist))]

    def _thread_final(self) -> None:
        logger.info("plot capture DONE")

        self._ready.set()

    def _start_thread(self) -> None:
        # get samples
        for j, pdata in enumerate(self._plot.qdlist):
            # get data from queue
            data = pdata.queue_get(block=True, timeout=1)

            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[j] >= self._samples:
                    continue

            # store data
            ydata: list[list] = [[] for v in range(pdata.vdim)]
            for sample in data:
                for i in range(pdata.vdim):
                    # TODO: metadata not supported for now
                    ydata[i].append(sample[0][i])

            # extend ydata
            self._plot.plist[j].ydata_extend(ydata)
            # get data len
            self._datalen[j] = len(self._plot.plist[j].ydata[0])

        # break loop if done
        if self._is_done(self._datalen):
            self._stop_set()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop capture plugin."""
        self._stop_flag.set()

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """
        if self._nostop:  # pragma: no cover
            return True
        else:
            return self._ready.wait(timeout)

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

        self.thread_start()

        return True

    def result(self) -> "PluginPlotMpl":
        """Get capture plugin result."""
        assert self._plot

        if self._write:  # pragma: no cover
            for pdata in self._plot.plist:
                pdata.plot()
            self._plot.fig.savefig(self._write)

        return self._plot
