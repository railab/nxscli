"""Module containing Numpy capture plugin."""

from typing import TYPE_CHECKING, Any

import numpy as np

from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.idata import PluginData, PluginQueueData

###############################################################################
# Class: PluginNpsave
###############################################################################


class PluginNpsave(PluginThread, IPluginFile):
    """Plugin that capture data to Numpy file."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._npdata: list[Any] = []

    def _init(self) -> None:
        assert self._phandler

        self._npdata = [[] for _ in range(len(self._data.qdlist))]
        for i, pdata in enumerate(self._data.qdlist):
            self._npdata[i] = [[] for v in range(pdata.vdim)]

    def _final(self) -> None:
        logger.info("numpy save captures DONE")

        for i, pdata in enumerate(self._data.qdlist):
            chanpath = self._path + "_chan" + str(pdata.chan) + ".npy"
            npdata = np.array(self._npdata[i])
            np.save(chanpath, npdata)

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        # store data
        for sample in data:
            for i in range(pdata.vdim):
                # TODO: metadata not supported for now
                self._npdata[j][i].append(sample.data[i])

        # get data len
        self._datalen[j] = len(self._npdata[j][0])

    def start(self, kwargs: Any) -> bool:
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

        self.thread_start(self._data)

        return True

    def result(self) -> None:
        """Get npsave plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
