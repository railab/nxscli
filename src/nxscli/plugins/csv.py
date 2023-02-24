"""Module containing CSV plugin."""

import csv
from typing import TYPE_CHECKING, Any

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream


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

    def _sample_row_get(self, sample: "DNxscopeStream") -> tuple[Any, Any]:
        # covert to string
        if self._meta_string:
            return (sample.data, bytes(list(sample.meta)).decode())
        else:
            return sample.data, sample.meta

    def _init(self) -> None:
        assert self._phandler
        # open writers
        self._csvwriters = self._csvwriters_open()

    def _final(self) -> None:
        # close all files
        for csvwriter in self._csvwriters:
            csvwriter[1].close()

        logger.info("csv capture DONE")

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        # store data
        for sample in data:
            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[j] >= self._samples:
                    break

            # write row
            self._csvwriters[j][0].writerow(self._sample_row_get(sample))

            # one sample
            self._datalen[j] += 1

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
