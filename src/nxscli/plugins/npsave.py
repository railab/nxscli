"""Module containing Numpy capture plugin."""

import threading
from typing import TYPE_CHECKING

import numpy as np
from nxslib.thread import ThreadCommon

from nxscli.iplugin import IPluginFile
from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.idata import PluginData

###############################################################################
# Class: PluginNpsave
###############################################################################


class PluginNpsave(IPluginFile, ThreadCommon):
    """Plugin that capture data to Numpy file."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        ThreadCommon.__init__(
            self, self._start_thread, self._thread_init, self._thread_final
        )

        self._samples: int
        self._data: "PluginData"
        self._path: str
        self._npdata: list = []
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

        self._datalen = [0 for _ in range(len(self._data.qdlist))]
        self._npdata = [[] for _ in range(len(self._data.qdlist))]

        for i, pdata in enumerate(self._data.qdlist):
            self._npdata[i] = [[] for v in range(pdata.vdim)]

    def _thread_final(self) -> None:
        logger.info("save captures DONE")

        for i, pdata in enumerate(self._data.qdlist):
            chanpath = self._path + "_chan" + str(pdata.chan) + ".npy"
            npdata = np.array(self._npdata[i])
            np.save(chanpath, npdata)

        self._ready.set()

    def _start_thread(self) -> None:
        # get samples
        for j, pdata in enumerate(self._data.qdlist):
            # get data from queue
            data = pdata.queue_get(block=True, timeout=1)

            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[j] >= self._samples:
                    continue

            # store data
            for sample in data:
                for i in range(pdata.vdim):
                    # TODO: metadata not supported for now
                    self._npdata[j][i].append(sample[0][i])

            # get data len
            self._datalen[j] = len(self._npdata[j][0])

        # break loop if done
        if self._is_done(self._datalen):
            self._stop_set()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop capture plugin."""
        self.thread_stop()

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
        self._path = kwargs["path"]
        self._nostop = kwargs["nostop"]

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        self._data = self._phandler.data_handler(chanlist, trig)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start()

        return True

    def result(self) -> None:
        """Get npsave plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
