"""Shared transform pipeline for fan-out processing over one sample stream."""

from collections import deque
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence

import numpy as np

from nxscli.transforms.window_engine import (
    latest_window,
    normalize_window_config,
)


class TransformProcessor(Protocol):
    """Protocol for processors used by ``TransformPipeline``."""

    @property
    def name(self) -> str:
        """Processor output name."""

    def process(self, store: "SampleStore") -> object | None:
        """Return transformed output or ``None`` when not ready."""


class SampleStore:
    """In-memory sample storage shared by all processors."""

    def __init__(self, max_points: int | None = None) -> None:
        """Initialize store.

        :param max_points: max points kept per channel, unbounded if ``None``.
        """
        self._max_points = max_points
        self._series: dict[str, deque[float]] = {}
        self._count: dict[str, int] = {}

    def ingest(self, batch: Mapping[str, Sequence[float]]) -> None:
        """Append a sample batch into the store."""
        for channel, values in batch.items():
            data = self._series.get(channel)
            if data is None:
                data = deque(maxlen=self._max_points)
                self._series[channel] = data
                self._count[channel] = 0
            for value in values:
                data.append(float(value))
                self._count[channel] += 1

    def count(self, channel: str) -> int:
        """Return number of ingested samples for channel."""
        return self._count.get(channel, 0)

    def series(self, channel: str) -> np.ndarray:
        """Return current channel series as float64 array."""
        values = self._series.get(channel)
        if values is None:
            return np.asarray([], dtype=np.float64)
        return np.asarray(list(values), dtype=np.float64)


class TransformPipeline:
    """Shared sample pipeline dispatching to many processors."""

    def __init__(self, *, max_points: int | None = None) -> None:
        """Initialize empty pipeline."""
        self._store = SampleStore(max_points=max_points)
        self._processors: list[TransformProcessor] = []

    @property
    def store(self) -> SampleStore:
        """Get shared sample store."""
        return self._store

    def register(self, processor: TransformProcessor) -> None:
        """Register one processor."""
        self._processors.append(processor)

    def ingest(
        self, batch: Mapping[str, Sequence[float]]
    ) -> dict[str, object]:
        """Ingest data and return outputs from ready processors."""
        self._store.ingest(batch)
        ret: dict[str, object] = {}
        for processor in self._processors:
            value = processor.process(self._store)
            if value is not None:
                ret[processor.name] = value
        return ret


@dataclass
class HopGate:
    """Per-processor hop gate used by windowed processors."""

    hop: int
    last_count: int = 0

    def ready(self, total_count: int) -> bool:
        """Return ``True`` when processor should run for current count."""
        if total_count <= 0:
            return False
        if self.last_count == 0:
            self.last_count = total_count
            return True
        if total_count - self.last_count >= self.hop:
            self.last_count = total_count
            return True
        return False


class WindowUnaryProcessor:
    """Windowed processor based on one source channel."""

    def __init__(
        self,
        *,
        name: str,
        channel: str,
        window: int,
        hop: int | None,
        fn: Callable[[np.ndarray], object],
    ) -> None:
        """Initialize unary processor."""
        self._name = name
        self._channel = channel
        self._cfg = normalize_window_config(window, hop)
        self._gate = HopGate(hop=self._cfg.hop)
        self._fn = fn

    @property
    def name(self) -> str:
        """Processor output name."""
        return self._name

    def process(self, store: SampleStore) -> object | None:
        """Process latest channel window when hop gate allows it."""
        total = store.count(self._channel)
        if not self._gate.ready(total):
            return None
        series = store.series(self._channel)
        window = latest_window(series.tolist(), self._cfg)
        return self._fn(window)


class WindowBinaryProcessor:
    """Windowed processor based on two source channels."""

    def __init__(
        self,
        *,
        name: str,
        left_channel: str,
        right_channel: str,
        window: int,
        hop: int | None,
        fn: Callable[[np.ndarray, np.ndarray], object],
    ) -> None:
        """Initialize binary processor."""
        self._name = name
        self._left_channel = left_channel
        self._right_channel = right_channel
        self._cfg = normalize_window_config(window, hop)
        self._gate = HopGate(hop=self._cfg.hop)
        self._fn = fn

    @property
    def name(self) -> str:
        """Processor output name."""
        return self._name

    def process(self, store: SampleStore) -> object | None:
        """Process latest pair of windows when hop gate allows it."""
        total = min(
            store.count(self._left_channel),
            store.count(self._right_channel),
        )
        if not self._gate.ready(total):
            return None
        left_series = store.series(self._left_channel)
        right_series = store.series(self._right_channel)
        left = latest_window(left_series.tolist(), self._cfg)
        right = latest_window(right_series.tolist(), self._cfg)
        size = min(int(left.size), int(right.size))
        return self._fn(left[-size:], right[-size:])
