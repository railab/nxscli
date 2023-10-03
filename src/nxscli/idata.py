"""Module containing common plugin data definition."""

import queue
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nxscli.logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from nxslib.dev import DeviceChannel
    from nxslib.nxscope import DNxscopeStream

    from nxscli.trigger import TriggerHandler

###############################################################################
# Class: PluginDataCb
###############################################################################


@dataclass
class PluginDataCb:
    """Plugin data callbacks."""

    stream_sub: "Callable[[int], queue.Queue[Any]]"
    stream_unsub: "Callable[[queue.Queue[Any]], None]"


###############################################################################
# Class: PluginQueueData
###############################################################################


class PluginQueueData:
    """The class used to handler stream queue data."""

    def __init__(
        self,
        que: queue.Queue[Any],
        channel: "DeviceChannel",
        trig: "TriggerHandler",
    ):
        """Initialize a queue data handler.

        :param que: queue subscribed to a given channel
        :param channel: instance of a channel
        :param dtc: trigger configuration
        """
        self._queue = que
        self._channel = channel
        self._trigger = trig

    def __str__(self) -> str:
        """Format string representation."""
        _str = (
            "PluginQueueData"
            + "(channel="
            + str(self._channel.data.chan)
            + ")"
        )
        return _str

    @property
    def queue(self) -> queue.Queue[Any]:
        """Get queue handler."""
        return self._queue

    @property
    def chan(self) -> int:
        """Get channel number."""
        return self._channel.data.chan

    @property
    def channame(self) -> str:
        """Get channel name."""
        return self._channel.data.name

    @property
    def is_numerical(self) -> bool:
        """Return true if this channel is numerical."""
        return self._channel.data.is_numerical

    @property
    def vdim(self) -> int:
        """Return stream data dimension."""
        return self._channel.data.vdim

    @property
    def mlen(self) -> int:
        """Return stream metadata dimension."""
        return self._channel.data.mlen

    def queue_get(
        self, block: bool, timeout: float = 1.0
    ) -> list["DNxscopeStream"]:
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
        return self._trigger.data_triggered(ret)


###############################################################################
# Class: PluginData
###############################################################################


class PluginData:
    """A common plugin data handler."""

    def __init__(
        self,
        chanlist: list["DeviceChannel"],
        trig: list["TriggerHandler"],
        cb: PluginDataCb,
    ):
        """Initialize a plugin data handler.

        :param chanlist: a list with plugin channels
        :param cb: plugin callback to nxslib
        """
        logger.info("prepare data %s", str(chanlist))
        assert len(chanlist) == len(trig)

        self._chanlist = chanlist
        self._trig = trig
        self._cb = cb

        # queue handlers
        self._qdlist = self._qdlist_init()

    def __del__(self) -> None:
        """Deinitialize queue handlers."""
        try:
            self._queue_deinit()
        except AttributeError:
            pass

    def _qdlist_init(self) -> list[PluginQueueData]:
        ret = []
        for i, channel in enumerate(self._chanlist):
            # get queue with data
            que = self._cb.stream_sub(channel.data.chan)
            # initialize queue handler
            pdata = PluginQueueData(que, channel, self._trig[i])
            # add hanler to a list
            ret.append(pdata)
        return ret

    def _queue_deinit(self) -> None:
        """Deinitialize queue."""
        for i, pdata in enumerate(self._qdlist):
            self._cb.stream_unsub(pdata.queue)
            self._qdlist.pop(i)

        # clean up triggers
        # TODO: revisit where this beleong, here or in plugins ?
        for trig in self._trig:
            trig.cleanup()

    @property
    def qdlist(self) -> list[PluginQueueData]:
        """Get queue data handlers."""
        return self._qdlist
