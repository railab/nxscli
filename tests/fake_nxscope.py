import queue
from types import SimpleNamespace
from typing import Any

from nxslib.dev import DeviceChannel


class FakeNxscope:
    """Fast Nxscope test double used by CLI/PluginHandler tests."""

    def __init__(self, *_: Any, **__: Any) -> None:
        self.connected = False
        self._stream_started = False
        self._channels = []
        for i in range(10):
            if i == 8:
                vdim = 0
            elif i == 9:
                vdim = 3
            else:
                vdim = 1
            self._channels.append(DeviceChannel(i, 10, vdim, f"chan{i}"))
        self.dev = SimpleNamespace(
            data=SimpleNamespace(chmax=len(self._channels))
        )
        self._enabled = [False for _ in self._channels]
        self._dividers = [0 for _ in self._channels]

    def __enter__(self) -> "FakeNxscope":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False
        self._stream_started = False

    def dev_channel_get(self, chid: int) -> DeviceChannel | None:
        if 0 <= chid < len(self._channels):
            return self._channels[chid]
        return None

    def channels_default_cfg(self) -> None:
        self._enabled = [False for _ in self._channels]
        self._dividers = [0 for _ in self._channels]

    def ch_enable(self, chid: int) -> None:
        self._enabled[chid] = True

    def ch_divider(self, chid: int, div: int) -> None:
        self._dividers[chid] = div

    def channels_write(self) -> None:
        return

    def stream_start(self) -> None:
        self._stream_started = True

    def stream_stop(self) -> None:
        self._stream_started = False

    def stream_sub(self, chid: int) -> queue.Queue[Any]:
        q: queue.Queue[Any] = queue.Queue()
        sample = SimpleNamespace(data=[float(chid)], meta=[0])
        # One large batch keeps plugin loops deterministic and fast.
        q.put([sample for _ in range(1200)])
        return q

    def stream_unsub(self, _: queue.Queue[Any]) -> None:
        return

    def get_enabled_channels(self, applied: bool = True) -> tuple[int, ...]:
        del applied
        return tuple(i for i, enabled in enumerate(self._enabled) if enabled)

    def get_channel_divider(self, chid: int, applied: bool = True) -> int:
        del applied
        return self._dividers[chid]

    def get_channel_dividers(self, applied: bool = True) -> tuple[int, ...]:
        del applied
        return tuple(self._dividers)

    def get_channels_state(self, applied: bool = True) -> Any:
        del applied
        return SimpleNamespace(
            enabled_channels=self.get_enabled_channels(),
            dividers=self.get_channel_dividers(),
        )

    def get_device_capabilities(self) -> Any:
        return SimpleNamespace(chmax=len(self._channels))

    def get_stream_stats(self) -> Any:
        return SimpleNamespace(
            connected=self.connected,
            stream_started=self._stream_started,
        )
