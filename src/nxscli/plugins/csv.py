"""Module containing CSV plugin."""  # noqa: A005

import csv
from typing import Any

import numpy as np

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread, StreamBlocks

###############################################################################
# Class: PluginCsv
###############################################################################


class PluginCsv(PluginThread, IPluginFile):
    """Plugin that capture data to CSV files."""

    def __init__(self) -> None:
        """Initialize a CSV plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._meta_string = False
        self._csvwriters: list[Any] = []

    def _csvwriters_open(self) -> list[Any]:
        csvwriters = []
        for pdata in self._data.qdlist:
            chanpath = self._path + "_chan" + str(pdata.chan) + ".csv"
            csvfile = open(chanpath, "w", newline="")
            csvwriter = csv.writer(
                csvfile,
                delimiter=" ",
                quotechar="|",
                escapechar="\\",
                quoting=csv.QUOTE_MINIMAL,
            )

            csvwriters.append([csvwriter, csvfile])

        return csvwriters

    def _init(self) -> None:
        assert self._phandler
        # open writers
        self._csvwriters = self._csvwriters_open()

    def _final(self) -> None:
        # close all files
        for csvwriter in self._csvwriters:
            csvwriter[1].close()

        logger.info("csv capture DONE")

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        writer = self._csvwriters[j][0]
        for block in data:
            block_data = block.data
            assert isinstance(block_data, np.ndarray)
            rows = int(block_data.shape[0])
            if rows == 0:
                continue

            if not self._nostop:  # pragma: no cover
                remaining = self._samples - self._datalen[j]
                if remaining <= 0:
                    break
                rows = min(rows, remaining)
                if rows <= 0:  # pragma: no cover
                    break

            data_rows = (tuple(row) for row in block_data[:rows])
            meta_rows: Any
            if block.meta is None:
                meta_rows = (() for _ in range(rows))
            elif self._meta_string:
                meta_rows = (
                    bytes(np.asarray(mrow, dtype=np.uint8)).decode()
                    for mrow in block.meta[:rows]
                )
            else:
                meta_rows = (tuple(mrow) for mrow in block.meta[:rows])

            writer.writerows(zip(data_rows, meta_rows))
            self._datalen[j] += rows

    def start(self, kwargs: Any) -> bool:
        """Start CSV plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start csv %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._path = kwargs["path"]
        self._meta_string = kwargs["metastr"]
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
        """Get CSV plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
