"""Module containing Numpy capture plugin."""

from typing import TYPE_CHECKING, Any

import numpy as np

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread, StreamBlocks

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream


class PluginNpsave(PluginThread, IPluginFile):
    """Plugin that capture data to Numpy file."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._npdata: list[list[np.ndarray[Any, Any]]] = []

    def _init(self) -> None:
        assert self._phandler

        self._npdata = [[] for _ in range(len(self._data.qdlist))]

    def _final(self) -> None:
        logger.info("numpy save captures DONE")

        for i, pdata in enumerate(self._data.qdlist):
            chanpath = self._path + "_chan" + str(pdata.chan) + ".npy"
            chunks = self._npdata[i]
            if chunks:
                npdata = np.concatenate(chunks, axis=0).T
            else:
                npdata = np.empty((pdata.vdim, 0), dtype=np.float64)
            np.save(chanpath, npdata)

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        rows = 0
        for block in data:
            block_data = np.asarray(block.data, dtype=np.float64)
            if int(block_data.shape[0]) == 0:  # pragma: no cover
                continue
            self._npdata[j].append(block_data)
            rows += int(block_data.shape[0])
        self._datalen[j] += rows

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        if not data:  # pragma: no cover
            return
        block = np.empty((len(data), pdata.vdim), dtype=np.float64)
        for row, sample in enumerate(data):
            for col in range(pdata.vdim):
                # TODO: metadata not supported for now
                block[row, col] = sample.data[col]
        self._npdata[j].append(block)
        self._datalen[j] += int(block.shape[0])

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
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

        cb = self._phandler.cb_get()
        self._data = PluginData(chanlist, trig, cb)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start(self._data)

        return True

    def result(self) -> None:
        """Get npsave plugin result."""
        return  # pragma: no cover
