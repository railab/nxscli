"""Module containing CSV plugin."""

import csv
import threading
from typing import TYPE_CHECKING

from nxslib.thread import ThreadCommon

from nxscli.iplugin import IPluginFile
from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.idata import PluginData


###############################################################################
# Class: PluginCsv
###############################################################################


class PluginCsv(IPluginFile, ThreadCommon):
    """Plugin that capture data to CSV files."""

    def __init__(self) -> None:
        """Initialize a CSV plugin."""
        IPluginFile.__init__(self)
        ThreadCommon.__init__(
            self, self._start_thread, self._thread_init, self._thread_final
        )

        self._samples: int
        self._data: "PluginData"
        self._path: str
        self._ready = threading.Event()
        self._meta_string = False
        self._nostop = False
        self._csvwriters: list = []
        self._datalen: list[int] = []

    def _csvwriters_open(self) -> list:
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

    def _sample_row_get(self, sample: tuple) -> tuple:
        # covert to string
        if self._meta_string:
            return (sample[0], bytes(list(sample[1])).decode())
        else:
            return sample

    def _thread_init(self) -> None:
        assert self._phandler
        # open writers
        self._csvwriters = self._csvwriters_open()

        self._datalen = [0 for _ in range(len(self._data.qdlist))]

    def _thread_final(self) -> None:
        # close all files
        for csvwriter in self._csvwriters:
            csvwriter[1].close()

        logger.info("csv capture DONE")

        self._ready.set()

    def _start_thread(self) -> None:
        # get samples
        for i, pdata in enumerate(self._data.qdlist):
            # get data from queue
            data = pdata.queue_get(block=True, timeout=0.1)

            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[i] >= self._samples:
                    continue

            # store data
            for sample in data:
                if not self._nostop:  # pragma: no cover
                    # ignore data if capture done for channel
                    if self._datalen[i] >= self._samples:
                        break

                # write row
                self._csvwriters[i][0].writerow(self._sample_row_get(sample))

                # one sample
                self._datalen[i] += 1

        # break loop if done
        if self._is_done(self._datalen):
            self._stop_set()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop CSV plugin."""
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

        self._data = self._phandler.data_handler(chanlist)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start()

        return True

    def result(self) -> None:
        """Get CSV plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
