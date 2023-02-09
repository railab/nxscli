"""Module containing common plugin data definition."""

import queue
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from nxslib.dev import DeviceChannel

###############################################################################
# Class: PluginDataCb
###############################################################################


@dataclass
class PluginDataCb:
    """Plugin data callbacks."""

    stream_sub: "Callable[[int], queue.Queue]"
    stream_unsub: "Callable[[int, queue.Queue], None]"


###############################################################################
# Class: PluginQueueData
###############################################################################


class PluginQueueData:
    """The class used to handler stream queue data."""

    def __init__(self, que: queue.Queue, channel: "DeviceChannel"):
        """Initialize a queue data handler.

        :param que: queue subscribed to a given channel
        :param channel: instance of a channel
        """
        self._queue = que
        self._channel = channel

    def __str__(self) -> str:
        """Format string representation."""
        _str = "PluginQueueData" + "(channel=" + str(self._channel.chan) + ")"
        return _str

    @property
    def queue(self) -> queue.Queue:
        """Get queue handler."""
        return self._queue

    @property
    def chan(self) -> int:
        """Get channel number."""
        return self._channel.chan

    @property
    def is_numerical(self) -> bool:
        """Return true if this channel is numerical."""
        return self._channel.is_numerical

    @property
    def vdim(self) -> int:
        """Return stream data dimension."""
        return self._channel.vdim

    @property
    def mlen(self) -> int:
        """Return stream metadata dimension."""
        return self._channel.mlen

    def queue_get(self, block: bool, timeout: float = 1.0) -> list:
        """Get data from a stream queue.

        :param block: blocking operation
        :param timeout: get data timeout
        """
        ret = []
        try:
            # get data from queue
            ret = self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            pass
        return ret


###############################################################################
# Class: PluginData
###############################################################################


class PluginData:
    """A common plugin data handler."""

    def __init__(self, chanlist: list["DeviceChannel"], cb: PluginDataCb):
        """Initialize a plugin data handler.

        :param chanlist: a list with plugin channels
        :param cb: plugin callback to nxslib
        """
        self._qdlist = []

        if not isinstance(cb, PluginDataCb):
            raise ValueError

        self._chanlist = chanlist
        self._cb = cb

        # queue handlers
        self._qdlist = self._qdlist_init()

    def __del__(self) -> None:
        """Deinitialize queue handlers."""
        self._queue_deinit()

    def _qdlist_init(self) -> list[PluginQueueData]:
        ret = []
        for channel in self._chanlist:
            # initialize plot
            que = self._cb.stream_sub(channel.chan)
            pdata = PluginQueueData(que, channel)
            # add plot to list
            ret.append(pdata)
        return ret

    def _queue_deinit(self) -> None:
        """Deinitialize queue."""
        for i, pdata in enumerate(self._qdlist):
            self._cb.stream_unsub(pdata.chan, pdata.queue)
            self._qdlist.pop(i)

    @property
    def qdlist(self) -> list[PluginQueueData]:
        """Get queue data handlers."""
        return self._qdlist
