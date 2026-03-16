"""Module containing Numpy memmap plugin."""

from typing import TYPE_CHECKING, Any

import numpy as np

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread, StreamBlocks

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream


class PluginNpmem(PluginThread, IPluginFile):
    """Plugin that capture data to Numpy memmap files."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._npfiles: list[Any] = []

        self._npshape: int
        self._npdata: list[np.ndarray[Any, Any]] = []

    def _init(self) -> None:
        assert self._phandler

        self._npdata = []

        for pdata in self._data.qdlist:
            chanpath = self._path + "_chan" + str(pdata.chan) + ".dat"
            npf = np.memmap(
                chanpath,
                dtype="float32",
                mode="w+",
                shape=(pdata.vdim, self._npshape),
            )
            self._npfiles.append(npf)
            self._npdata.append(np.empty((0, pdata.vdim), dtype=np.float64))

    def _final(self) -> None:
        logger.info("numpy memmap captures DONE")

        # no API to close memmap

    def _flush_ready(self, pdata: "PluginQueueData", j: int) -> None:
        pending = self._npdata[j]
        while pending.shape[0] >= self._npshape:
            chunk = pending[: self._npshape, :]
            self._npfiles[j][:] = chunk.T.astype(np.float32, copy=False)
            self._npfiles[j].flush()
            self._datalen[j] += self._npshape
            pending = pending[self._npshape :, :]
        self._npdata[j] = pending

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        chunks: list[np.ndarray[Any, Any]] = [self._npdata[j]]
        for block in data:
            block_data = np.asarray(block.data, dtype=np.float64)
            if int(block_data.shape[0]) == 0:  # pragma: no cover
                continue
            chunks.append(block_data)
        if len(chunks) > 1:  # pragma: no branch
            self._npdata[j] = np.concatenate(chunks, axis=0)
        self._flush_ready(pdata, j)

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
        self._npdata[j] = np.concatenate((self._npdata[j], block), axis=0)
        self._flush_ready(pdata, j)

    def start(self, kwargs: Any) -> bool:  # pragma: no cover
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

        cb = self._phandler.cb_get()
        self._data = PluginData(chanlist, trig, cb)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start(self._data)

        return True

    def result(self) -> None:
        """Get npsave plugin result."""
        return  # pragma: no cover
