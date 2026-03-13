"""Module containing dummy capture plugin."""

from typing import Any

import numpy as np

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginNone
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread, StreamBlocks

###############################################################################
# Class: PluginNone
###############################################################################


class PluginNone(PluginThread, IPluginNone):
    """Dummy plugin that do nothing with captured data."""

    def __init__(self) -> None:
        """Intiialize a none plugin."""
        IPluginNone.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"

    def _init(self) -> None:
        assert self._phandler

    def _final(self) -> None:
        logger.info("None DONE")

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        for block in data:
            block_data = block.data
            assert isinstance(block_data, np.ndarray)
            rows = int(block_data.shape[0])
            if rows == 0:
                continue
            if not self._nostop:
                remaining = self._samples - self._datalen[j]
                if remaining <= 0:
                    break
                rows = min(rows, remaining)
            self._datalen[j] += rows

    def start(self, kwargs: Any) -> bool:
        """Start none plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
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
        """Get none plugin result."""
        return  # pragma: no cover
