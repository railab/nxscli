"""Module containing capture plugin."""

import threading
from typing import TYPE_CHECKING

from nxscli.iplugin import IPluginPlotStatic
from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.plot_mpl import PluginPlotMpl

###############################################################################
# Class: PluginCapture
###############################################################################


# TODO: reuse misc/thread.py
class PluginCapture(IPluginPlotStatic):
    """Plugin that plot static captured data."""

    def __init__(self) -> None:
        """Intiialize a capture plot plugin."""
        super().__init__()

        self._thrd: threading.Thread
        self._samples: int
        self._plot: "PluginPlotMpl"
        self._write: str
        self._ready = threading.Event()
        self._stop_flag = threading.Event()
        self._nostop = False

        self._stop_flag.clear()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop capture plugin."""
        self._stop_flag.set()

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready."""
        if self._nostop:  # pragma: no cover
            return True
        else:
            return self._ready.wait(timeout)

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

    def _start_thread(self) -> None:
        assert self._phandler

        datalen = [0 for _ in range(len(self._plot.qdlist))]

        # get samples
        while not self._stop_flag.is_set():  # pragma: no cover
            for j, pdata in enumerate(self._plot.qdlist):
                # get data from queue
                data = pdata.queue_get(block=True, timeout=1)

                if not self._nostop:
                    # ignore data if capture done for channel
                    if datalen[j] >= self._samples:
                        continue

                # store data
                ydata: list[list] = [[] for v in range(pdata.vdim)]
                for sample in data:
                    for i in range(pdata.vdim):
                        ydata[i].append(sample[0][i])

                # extend ydata
                self._plot.plist[j].ydata_extend(ydata)
                # get data len
                datalen[j] = len(self._plot.plist[j].ydata[0])

            # break loop if done
            if self._is_done(datalen):
                break

        logger.info("plot capture DONE")

        # self._plot.queue_deinit()

        self._ready.set()

    def start(self, kwargs: dict) -> bool:
        """Start capture plugin."""
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._write = kwargs["write"]
        self._nostop = kwargs["nostop"]

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])

        self._plot = self._phandler.plot_handler(
            chanlist, dpi=kwargs["dpi"], fmt=kwargs["fmt"]
        )

        if not self._plot.qdlist or not self._plot.plist:  # pragma: no cover
            return False

        for pdata in self._plot.plist:
            # update xlim to fit our data
            if self._samples:
                pdata.set_xlim((0, self._samples))
            else:  # pragma: no cover
                pass

        self._thrd = threading.Thread(target=self._start_thread)
        self._thrd.start()

        return True

    def result(self) -> "PluginPlotMpl":
        """Get capture plugin result."""
        assert self._plot

        if self._write:  # pragma: no cover
            for pdata in self._plot.plist:
                pdata.plot()
            self._plot.fig.savefig(self._write)

        return self._plot
