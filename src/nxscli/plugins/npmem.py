"""Module containing Numpy memmap plugin."""

from typing import TYPE_CHECKING

import numpy as np

from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxscli.idata import PluginData, PluginQueueData

###############################################################################
# Class: PluginNpmem
###############################################################################


class PluginNpmem(PluginThread, IPluginFile):
    """Plugin that capture data to Numpy memmap files."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._npfiles: list = []

        self._npshape: int
        self._npdata: list = []

    def _init(self) -> None:
        assert self._phandler

        self._npdata = [[] for _ in range(len(self._data.qdlist))]
        for i, pdata in enumerate(self._data.qdlist):
            self._npdata[i] = [[] for v in range(pdata.vdim)]

        for pdata in self._data.qdlist:
            chanpath = self._path + "_chan" + str(pdata.chan) + ".dat"
            # TODO: get channel type
            npf = np.memmap(
                chanpath,
                dtype="float32",
                mode="w+",
                shape=(pdata.vdim, self._npshape),
            )
            self._npfiles.append(npf)

    def _final(self) -> None:
        logger.info("numpy memmap captures DONE")

        # no API to close memmap

    def _handle_samples(
        self, data: list, pdata: "PluginQueueData", j: int
    ) -> None:
        for sample in data:
            for i in range(pdata.vdim):
                # TODO: metadata not supported for now
                self._npdata[j][i].append(sample[0][i])

        # put data on mememap
        if len(self._npdata[j][0]) >= self._npshape:
            for i in range(pdata.vdim):
                # store remaining data
                tmp = self._npdata[j][i][: self._npshape]
                # get data with a proper shape
                self._npdata[j][i] = self._npdata[j][i][self._npshape :]

            # update memmap data
            self._npfiles[j][:] = tmp
            self._npfiles[j].flush()

            # get data len
            self._datalen[j] += self._npshape

    def start(self, kwargs: dict) -> bool:
        """Start capture plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._path = kwargs["path"]
        self._nostop = kwargs["nostop"]
        self._npshape = kwargs["shape"]

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
