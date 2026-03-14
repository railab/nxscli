"""Shared virtual-channel runtime for nxscli stream pipeline."""

import queue
from dataclasses import dataclass
from threading import Lock
from time import sleep
from typing import TYPE_CHECKING

import numpy as np
from nxslib.dev import DeviceChannel
from nxslib.nxscope import DNxscopeStreamBlock, NxscopeHandler
from nxslib.thread import ThreadCommon

from nxscli.virtual.errors import VirtualChannelError
from nxscli.virtual.manager import VirtualChannelManager
from nxscli.virtual.models import SampleValue, VirtualChannelSpec

if TYPE_CHECKING:
    from nxscli.channelref import ChannelRef


@dataclass(frozen=True)
class DeclaredVirtualChannel:
    """One declared virtual channel with fixed output aliases."""

    spec: VirtualChannelSpec
    output_ids: tuple[str, ...]
    aliases: tuple[str, ...]
    aliased_names: tuple[str, ...]


class VirtualStreamRuntime:
    """Expose virtual channels as normal stream channels."""

    def __init__(self) -> None:
        """Initialize runtime state."""
        self._lock = Lock()
        self._nxscope: NxscopeHandler | None = None
        self._manager = VirtualChannelManager()
        self._declared: list[DeclaredVirtualChannel] = []
        self._alias_to_output_id: dict[str, str] = {}
        self._output_id_to_alias: dict[str, str] = {}
        self._channels: dict[str, DeviceChannel] = {}
        self._subscribers: dict[
            str, list[queue.Queue[list[DNxscopeStreamBlock]]]
        ] = {}
        self._physical_subs: dict[
            int, queue.Queue[list[DNxscopeStreamBlock]]
        ] = {}
        self._thread = ThreadCommon(self._thread_common, name="virtstream")
        self._poll_idx = 0
        self._started = False

    def add_virtual_channel(
        self,
        channel_id: int,
        name: str,
        operator: str,
        inputs: tuple[str, ...],
        params: dict[str, object],
    ) -> tuple[tuple[str, str], ...]:
        """Add one virtual channel declaration.

        :return: tuple of ``(alias_channel_id, internal_output_id)``
        """
        if channel_id < 0:
            raise VirtualChannelError("virtual channel id must be >= 0")

        with self._lock:
            base = f"v{channel_id}"
            output_ids: tuple[str, ...]
            aliases: tuple[str, ...]
            alias_names: tuple[str, ...]
            if operator == "stats_running":
                output_ids = (
                    f"{base}.min",
                    f"{base}.max",
                    f"{base}.avg",
                    f"{base}.rms",
                )
                aliases = (
                    f"v{channel_id}",
                    f"v{channel_id + 1}",
                    f"v{channel_id + 2}",
                    f"v{channel_id + 3}",
                )
                alias_names = (
                    f"v{channel_id}",
                    f"v{channel_id + 1}",
                    f"v{channel_id + 2}",
                    f"v{channel_id + 3}",
                )
            else:
                output_ids = (base,)
                aliases = (f"v{channel_id}",)
                alias_names = (f"v{channel_id}",)

            for out_id in output_ids:
                if out_id in self._output_id_to_alias:
                    raise VirtualChannelError(
                        f"virtual output already exists: {out_id}"
                    )
            for alias_name in alias_names:
                if alias_name in self._alias_to_output_id:
                    raise VirtualChannelError(
                        f"virtual alias already exists: {alias_name}"
                    )

            resolved_inputs = tuple(
                self._alias_to_output_id.get(
                    self._normalize_input_token(token), token
                )
                for token in inputs
            )
            spec = VirtualChannelSpec(
                channel_id=base,
                name=name,
                operator=operator,
                inputs=resolved_inputs,
                params=dict(params),
            )
            self._declared.append(
                DeclaredVirtualChannel(
                    spec=spec,
                    output_ids=output_ids,
                    aliases=aliases,
                    aliased_names=alias_names,
                )
            )
            for out_id, alias in zip(output_ids, aliases):
                self._output_id_to_alias[out_id] = alias
            for out_id, alias_name in zip(output_ids, alias_names):
                self._alias_to_output_id[alias_name] = out_id

            if self._nxscope is not None:
                self._rebuild_locked()

        return tuple(
            (alias, out_id) for alias, out_id in zip(aliases, output_ids)
        )

    def clear(self) -> None:
        """Remove all declared virtual channels."""
        with self._lock:
            self._declared = []
            self._alias_to_output_id = {}
            self._output_id_to_alias = {}
            self._channels = {}
            self._subscribers = {}
            self._manager = VirtualChannelManager()

    def declared(self) -> tuple[DeclaredVirtualChannel, ...]:
        """Return current declarations."""
        with self._lock:
            return tuple(self._declared)

    def channel_get(self, channel: "ChannelRef") -> DeviceChannel | None:
        """Return runtime channel metadata."""
        if not channel.is_virtual:
            return None
        chid = channel.virtual_name()
        with self._lock:
            return self._channels.get(chid)

    def channel_list(self) -> tuple[DeviceChannel, ...]:
        """Return all runtime channels."""
        with self._lock:
            return tuple(self._channels.values())

    def stream_sub(
        self, channel: "ChannelRef"
    ) -> queue.Queue[list[DNxscopeStreamBlock]] | None:
        """Subscribe queue for virtual channel."""
        if not channel.is_virtual:
            return None
        chan = channel.virtual_name()
        with self._lock:
            if chan not in self._channels:
                return None
            subq: queue.Queue[list[DNxscopeStreamBlock]] = queue.Queue()
            self._subscribers.setdefault(chan, []).append(subq)
            return subq

    def stream_unsub(
        self, subq: queue.Queue[list[DNxscopeStreamBlock]]
    ) -> bool:
        """Unsubscribe queue. Returns ``True`` if removed."""
        with self._lock:
            for chan in list(self._subscribers.keys()):
                subs = self._subscribers[chan]
                if subq in subs:
                    subs.remove(subq)
                    if not subs:
                        del self._subscribers[chan]
                    return True
        return False

    def on_connect(self, nxscope: NxscopeHandler) -> None:
        """Attach runtime to connected Nxscope handler."""
        with self._lock:
            self._nxscope = nxscope
            self._rebuild_locked()

    def on_disconnect(self) -> None:
        """Detach runtime from Nxscope handler."""
        self.on_stream_stop()
        with self._lock:
            self._nxscope = None
            self._manager = VirtualChannelManager()
            self._channels = {}

    def on_stream_start(self) -> None:
        """Start runtime streaming thread."""
        with self._lock:
            if self._started:
                return
            if self._nxscope is None:
                return
            if not self._declared:
                return

            self._physical_subs = {}
            for channel_id in self._manager.required_physical_channel_ids():
                chid = int(channel_id)
                self._physical_subs[chid] = self._nxscope.stream_sub(chid)
            self._started = True

        self._thread.thread_start()

    def on_stream_stop(self) -> None:
        """Stop runtime streaming thread."""
        with self._lock:
            if not self._started:
                return
            self._started = False
        self._thread.thread_stop()
        with self._lock:
            if self._nxscope is not None:
                for subq in self._physical_subs.values():
                    self._nxscope.stream_unsub(subq)
            self._physical_subs = {}
            self._manager.reset()

    def _rebuild_locked(self) -> None:
        assert self._nxscope is not None
        assert self._nxscope.dev is not None

        manager = VirtualChannelManager()
        for chid in range(self._nxscope.dev.data.chmax):
            channel = self._nxscope.dev_channel_get(chid)
            if channel is not None and channel.data.is_valid:
                manager.add_physical_channel(channel)

        channels: dict[str, DeviceChannel] = {}
        chan_idx = -1
        for declared in self._declared:
            outputs = manager.add_virtual_channel(declared.spec)
            got_ids = tuple(out.channel_id for out in outputs)
            if got_ids != declared.output_ids:
                raise VirtualChannelError(
                    "virtual output ids mismatch for declared channel "
                    f"{declared.spec.channel_id}"
                )
            for output, alias in zip(outputs, declared.aliases):
                channels[alias] = DeviceChannel(
                    chan=chan_idx,
                    _type=output.dtype,
                    vdim=output.vdim,
                    name=alias,
                )
                chan_idx -= 1

        self._manager = manager
        self._channels = channels
        self._subscribers = {
            chan: self._subscribers.get(chan, []) for chan in channels
        }

    def _to_sample(self, sample: object) -> SampleValue | None:
        try:
            arr = np.asarray(sample, dtype=np.float64).reshape(-1)
            return tuple(float(x) for x in arr.tolist())
        except (TypeError, ValueError):
            return None

    def _normalize_input_token(self, token: str) -> str:
        tok = token.strip()
        if tok.startswith("v"):
            vid = tok[1:]
            if not vid.isnumeric():
                raise VirtualChannelError(
                    f"invalid virtual channel input: {token}"
                )
            return f"v{int(vid)}"
        return tok

    def _thread_common(self) -> None:
        with self._lock:
            subs = list(self._physical_subs.items())

        if not subs:
            sleep(0.05)
            return

        chid, subq = subs[self._poll_idx % len(subs)]
        self._poll_idx += 1
        try:
            batch = subq.get(block=True, timeout=0.05)
        except queue.Empty:
            return

        out_batches = self._process_batch(chid, batch)

        if not out_batches:
            return

        with self._lock:
            for alias, samples in out_batches.items():
                for qsub in self._subscribers.get(alias, []):
                    qsub.put(samples)

    def _process_batch(
        self,
        chid: int,
        batch: list[DNxscopeStreamBlock],
    ) -> dict[str, list[DNxscopeStreamBlock]]:
        out_rows = self._collect_output_rows(chid, batch)
        return self._build_output_blocks(out_rows)

    def _collect_output_rows(
        self,
        chid: int,
        batch: list[DNxscopeStreamBlock],
    ) -> dict[str, list[SampleValue]]:
        out_rows: dict[str, list[SampleValue]] = {}
        for item in batch:
            arr = item.data
            if int(arr.shape[0]) == 0:
                continue
            for row in arr:
                sample = self._to_sample(row)
                if sample is None:
                    continue
                try:
                    changed = self._manager.process_update(str(chid), sample)
                except VirtualChannelError:
                    continue
                for out_id, out_value in changed.items():
                    alias = self._output_id_to_alias.get(out_id)
                    if alias is None:
                        continue
                    out_rows.setdefault(alias, []).append(out_value)
        return out_rows

    def _build_output_blocks(
        self,
        out_rows: dict[str, list[SampleValue]],
    ) -> dict[str, list[DNxscopeStreamBlock]]:
        out_batches: dict[str, list[DNxscopeStreamBlock]] = {}
        for alias, rows in out_rows.items():
            chan = self._channels.get(alias)
            if chan is None or not rows:
                continue
            vdim = int(chan.data.vdim)
            arr = np.asarray(rows, dtype=np.float64).reshape(-1, vdim)
            out_batches[alias] = [DNxscopeStreamBlock(data=arr, meta=None)]

        return out_batches
