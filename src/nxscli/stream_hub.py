"""Shared physical stream fan-out provider for all plugins."""

import queue
from threading import Lock
from time import sleep
from typing import TYPE_CHECKING

from nxslib.thread import ThreadCommon

if TYPE_CHECKING:
    from nxslib.dev import DeviceChannel
    from nxslib.nxscope import DNxscopeStreamBlock, NxscopeHandler

    from nxscli.channelref import ChannelRef


class SharedStreamProvider:
    """Provide shared physical stream queues to many consumers."""

    def __init__(self) -> None:
        """Initialize provider state."""
        self._lock = Lock()
        self._nxscope: "NxscopeHandler | None" = None
        self._started = False
        self._source_subs: dict[
            int, queue.Queue[list["DNxscopeStreamBlock"]]
        ] = {}
        self._subscribers: dict[
            int, list[queue.Queue[list["DNxscopeStreamBlock"]]]
        ] = {}
        self._queue_to_channel: dict[int, int] = {}
        self._thread = ThreadCommon(self._thread_common, name="streamhub")
        self._poll_idx = 0

    def on_connect(self, nxscope: "NxscopeHandler") -> None:
        """Attach provider to active Nxscope handler."""
        with self._lock:
            self._nxscope = nxscope

    def on_disconnect(self) -> None:
        """Detach provider from Nxscope handler."""
        self.on_stream_stop()
        with self._lock:
            self._nxscope = None
            self._subscribers = {}
            self._queue_to_channel = {}

    def on_stream_start(self) -> None:
        """Start fan-out thread and source subscriptions."""
        with self._lock:
            if self._started:
                return
            if self._nxscope is None:
                return
            self._started = True
            for chid in self._subscribers:
                self._ensure_source_sub_locked(chid)
        self._thread.thread_start()

    def on_stream_stop(self) -> None:
        """Stop fan-out thread and upstream subscriptions."""
        with self._lock:
            if not self._started:
                return
            self._started = False
        self._thread.thread_stop()
        with self._lock:
            if self._nxscope is not None:
                for subq in self._source_subs.values():
                    self._nxscope.stream_unsub(subq)
            self._source_subs = {}

    def channel_get(self, channel: "ChannelRef") -> "DeviceChannel | None":
        """Return physical channel metadata from Nxscope."""
        with self._lock:
            if self._nxscope is None:
                return None
        if not channel.is_physical:
            return None
        return self._nxscope.dev_channel_get(channel.physical_id())

    def channel_list(self) -> tuple["DeviceChannel", ...]:
        """No extra virtual channels are provided by this hub."""
        return ()

    def stream_sub(
        self, channel: "ChannelRef"
    ) -> "queue.Queue[list[DNxscopeStreamBlock]] | None":
        """Subscribe to physical channel fan-out queue."""
        if not channel.is_physical:
            return None
        chid = channel.physical_id()
        with self._lock:
            subq: queue.Queue[list["DNxscopeStreamBlock"]] = queue.Queue()
            self._subscribers.setdefault(chid, []).append(subq)
            self._queue_to_channel[id(subq)] = chid
            if self._started:
                self._ensure_source_sub_locked(chid)
            return subq

    def stream_unsub(
        self, subq: "queue.Queue[list[DNxscopeStreamBlock]]"
    ) -> bool:
        """Unsubscribe consumer queue from fan-out."""
        with self._lock:
            qid = id(subq)
            chid = self._queue_to_channel.get(qid)
            if chid is None:
                return False
            self._queue_to_channel.pop(qid, None)
            subs = self._subscribers.get(chid, [])
            if subq in subs:
                subs.remove(subq)
            if not subs:
                self._subscribers.pop(chid, None)
                if self._nxscope is not None and chid in self._source_subs:
                    self._nxscope.stream_unsub(self._source_subs[chid])
                    self._source_subs.pop(chid, None)
            return True

    def _ensure_source_sub_locked(self, chid: int) -> None:
        if self._nxscope is None:
            return
        if chid in self._source_subs:
            return
        self._source_subs[chid] = self._nxscope.stream_sub(chid)

    def _thread_common(self) -> None:
        with self._lock:
            if not self._started:
                return
            if not self._source_subs:
                sleep(0.005)
                return
            items = list(self._source_subs.items())
            idx = self._poll_idx % len(items)
            self._poll_idx += 1
            chid, srcq = items[idx]
            dstq = list(self._subscribers.get(chid, []))

        try:
            blocks = srcq.get(block=True, timeout=0.02)
        except queue.Empty:
            return

        if not blocks:
            return

        for subq in dstq:
            subq.put(blocks)
