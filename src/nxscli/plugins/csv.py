"""Module containing CSV plugin."""

import csv
import threading
from typing import TYPE_CHECKING

from nxscli.iplugin import IPluginPlotFile
from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.idata import PluginData

###############################################################################
# Class: PluginCsv
###############################################################################


# TODO: reuse misc/thread.py
class PluginCsv(IPluginPlotFile):
    """Plugin that capture data to CSV files."""

    def __init__(self) -> None:
        """Initialize a CSV plugin."""
        super().__init__()

        self._thrd: threading.Thread
        self._samples: int
        self._data: "PluginData"
        self._path: str
        self._ready = threading.Event()
        self._meta_string = False
        self._stop_flag = threading.Event()
        self._nostop = False

        self._stop_flag.clear()

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

    def _start_thread(self) -> None:
        assert self._phandler

        # open writers
        csvwriters = self._csvwriters_open()

        datalen = [0 for _ in range(len(self._data.qdlist))]

        # get samples
        while not self._stop_flag.is_set():  # pragma: no cover
            for i, pdata in enumerate(self._data.qdlist):
                # get data from queue
                data = pdata.queue_get(block=True, timeout=1)

                if not self._nostop:
                    # ignore data if capture done for channel
                    if datalen[i] >= self._samples:
                        continue

                # store data
                for sample in data:
                    if not self._nostop:
                        # ignore data if capture done for channel
                        if datalen[i] >= self._samples:
                            break

                    # write row
                    csvwriters[i][0].writerow(self._sample_row_get(sample))

                    # one sample
                    datalen[i] += 1

            # break loop if done
            if self._is_done(datalen):
                self.stop()

        # close all files
        for csvwriter in csvwriters:
            csvwriter[1].close()

        logger.info("csv capture DONE")

        self._ready.set()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop CSV plugin."""
        self._stop_flag.set()

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

        self._thrd = threading.Thread(target=self._start_thread)
        self._thrd.start()

        return True

    def result(self) -> None:
        """Get CSV plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
