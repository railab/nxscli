"""Module containing Nxscli plugin thread common logic."""

import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from nxslib.thread import ThreadCommon

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.idata import PluginData, PluginQueueData


###############################################################################
# Class: PluginThread
###############################################################################


class PluginThread(ABC):
    """The Nxscli plugin thread."""

    def __init__(self) -> None:
        """Initialize a Nxslib plugin thread."""
        self._thread = ThreadCommon(
            self._thread_common, self._init_common, self._final_common
        )

        self._samples: int
        self._nostop = False
        self._ready = threading.Event()
        self._datalen: list[int] = []
        self._plugindata: "PluginData"

    def _thread_common(self) -> None:
        assert self._plugindata
        # get samples
        for j, pdata in enumerate(self._plugindata.qdlist):
            # get data from queue
            data = pdata.queue_get(block=True, timeout=1)

            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[j] >= self._samples:
                    continue

            # handle samples
            self._handle_samples(data, pdata, j)

        # break loop if done
        if self._is_done(self._datalen):
            self._thread.stop_set()

    def _init_common(self) -> None:
        self._init()
        self._datalen = [0 for _ in range(len(self._plugindata.qdlist))]

    def _final_common(self) -> None:
        self._final()
        self._ready.set()

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return True

    def stop(self) -> None:
        """Stop capture plugin."""
        self._thread.thread_stop()

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """
        if self._nostop:  # pragma: no cover
            return True
        return self._ready.wait(timeout)

    def thread_start(self, plugindata: "PluginData") -> None:
        """Start working thread."""
        self._plugindata = plugindata
        self._thread.thread_start()

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

    @abstractmethod
    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        """Handle samples from queue and update datalen."""

    @abstractmethod
    def _init(self) -> None:
        """Logic called before thread loop."""

    @abstractmethod
    def _final(self) -> None:
        """Logic called after thread loop."""
