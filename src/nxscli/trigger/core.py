"""Module containing Nxscli stream data trigger logic."""

import weakref
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, Any

import numpy as np
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.logger import logger

if TYPE_CHECKING:
    from nxscli.channelref import ChannelRef

###############################################################################
# Enum: ETriggerType
###############################################################################


class ETriggerType(Enum):
    """Trigger types."""

    ALWAYS_OFF = 0
    ALWAYS_ON = 1
    EDGE_RISING = 2
    EDGE_FALLING = 3
    WINDOW_ENTER = 4
    WINDOW_EXIT = 5


class ETriggerCaptureMode(Enum):
    """Trigger capture behavior."""

    START_AFTER = "start_after"
    STOP_AFTER = "stop_after"


###############################################################################
# Enum: DTriggerState
###############################################################################


@dataclass
class DTriggerState:
    """The class representing trigger state."""

    state: bool
    idx: int


@dataclass
class DTriggerEvent:
    """Metadata about one emitted trigger event."""

    sample_index: float
    channel: int
    capture_mode: ETriggerCaptureMode


###############################################################################
# Class: DDTriggerConfigReq
###############################################################################


@dataclass
class DTriggerConfigReq:
    """The class representing trigger configuration request."""

    ttype: str
    srcchan: "int | ChannelRef | None"
    vect: int = 0
    params: list[Any] | None = None
    mode: str | None = None
    pre_samples: int | None = None
    post_samples: int | None = None
    holdoff: int = 0
    rearm: bool = False


###############################################################################
# Function: trigger_from_req
###############################################################################


def trigger_from_req(req: DTriggerConfigReq) -> "DTriggerConfig":
    """Get trigger configuration from string.

    :param req: trigger configuration request
    """
    capture_mode = ETriggerCaptureMode.START_AFTER
    if req.mode is not None:
        capture_mode = ETriggerCaptureMode(req.mode)

    srcchan = req.srcchan if isinstance(req.srcchan, int) else None

    if req.ttype == "off":
        # no arguments
        dtc = DTriggerConfig(
            ETriggerType.ALWAYS_OFF, capture_mode=capture_mode
        )
    elif req.ttype == "on":
        # no arguments
        dtc = DTriggerConfig(ETriggerType.ALWAYS_ON, capture_mode=capture_mode)
    elif req.ttype == "er":
        # argument 1 horisontal offset
        # argument 2 trigger level
        assert req.params
        hoffset = int(req.params[0])
        level = float(req.params[1])
        dtc = DTriggerConfig(
            ETriggerType.EDGE_RISING,
            srcchan,
            req.vect,
            hoffset,
            level,
            capture_mode=capture_mode,
        )
    elif req.ttype == "ef":
        # argument 1 horisontal offset
        # argument 2 trigger level
        assert req.params
        hoffset = int(req.params[0])
        level = float(req.params[1])
        dtc = DTriggerConfig(
            ETriggerType.EDGE_FALLING,
            srcchan,
            req.vect,
            hoffset,
            level,
            capture_mode=capture_mode,
        )
    elif req.ttype == "we":
        assert req.params
        hoffset = int(req.params[0])
        low = float(req.params[1])
        high = float(req.params[2])
        dtc = DTriggerConfig(
            ETriggerType.WINDOW_ENTER,
            srcchan,
            req.vect,
            hoffset,
            window_low=low,
            window_high=high,
            capture_mode=capture_mode,
        )
    elif req.ttype == "wx":
        assert req.params
        hoffset = int(req.params[0])
        low = float(req.params[1])
        high = float(req.params[2])
        dtc = DTriggerConfig(
            ETriggerType.WINDOW_EXIT,
            srcchan,
            req.vect,
            hoffset,
            window_low=low,
            window_high=high,
            capture_mode=capture_mode,
        )
    else:
        raise AssertionError

    if req.pre_samples is not None:
        dtc.pre_samples = req.pre_samples
    if req.post_samples is not None:
        dtc.post_samples = req.post_samples
    dtc.holdoff = req.holdoff
    dtc.rearm = req.rearm
    return dtc


###############################################################################
# Class: DTriggerConfig
###############################################################################


@dataclass
class DTriggerConfig:
    """Trigger configuration."""

    ttype: ETriggerType
    srcchan: int | None = None
    vect: int = 0
    hoffset: int = 0
    level: float | None = None
    source_ref: "ChannelRef | None" = None
    window_low: float | None = None
    window_high: float | None = None
    capture_mode: ETriggerCaptureMode = ETriggerCaptureMode.START_AFTER
    pre_samples: int = 0
    post_samples: int = 0
    holdoff: int = 0
    rearm: bool = False

    @property
    def effective_pre_samples(self) -> int:
        """Return explicit pre-samples or fall back to legacy hoffset."""
        if self.pre_samples > 0:
            return self.pre_samples
        return self.hoffset


###############################################################################
# Class: TriggerHandler
###############################################################################


class TriggerHandler(object):
    """The class used to handler stream data trigger."""

    _instances: weakref.WeakSet["TriggerHandler"] = weakref.WeakSet()
    _wait_for_src: weakref.WeakSet["TriggerHandler"] = weakref.WeakSet()

    def __new__(cls, chan: int, config: DTriggerConfig) -> "TriggerHandler":
        """Create a new instance and store reference in a weak set."""
        instance = object.__new__(cls)
        cls._instances.add(instance)
        # create additional flag that helps during instance cleanup
        object.__setattr__(instance, "_initdone", False)
        return instance

    def __init__(self, chan: int, config: DTriggerConfig) -> None:
        """Initialize a stream data trigger handler."""
        self._config = config
        self._cache: list[Any] = []
        self._chan: int = chan
        self._trigger: DTriggerState = DTriggerState(False, 0)
        self._triger_done = False
        self._post_remaining = 0
        self._last_event: DTriggerEvent | None = None

        # trigger source channel reference
        self._src: "TriggerHandler" | None = None  # noqa: TC010
        # connected cross channels
        self._cross: list["TriggerHandler"] = []
        self._src_configured = False
        # configure cross trigger
        self._src_configured = True
        self._config_crosschan()

        # check pending cross channels
        self._pending_crosschan()

        # cross trigger status protected with lock
        self._lock = Lock()
        self._cross_trigger: DTriggerState = DTriggerState(False, 0)
        self._initdone = True

    def __del__(self) -> None:
        """Clean up."""
        self.cleanup()

    def _config_crosschan(self) -> None:
        # subscribe to source channel if needed
        src = None
        if self._config.srcchan is not None:
            # get the first available trigger related to srcchan
            for x in TriggerHandler._instances:
                if x.chan == self._config.srcchan:
                    src = x
                    break

            if not src:
                # not found source channel
                # trigger not configured yet
                self._src_configured = False
                # wait for source channel
                TriggerHandler._wait_for_src.add(self)
            else:
                # connect source
                self.source_set(src)
                # subscribe to source
                src.subscribe_cross(self)

    def _pending_crosschan(self) -> None:
        # check if any instance wait for us
        # NOTE: there can be many waiting instances
        tmp = []
        for inst in TriggerHandler._wait_for_src:
            if inst.config.srcchan == self.chan:
                # subscribe us and set source
                self.subscribe_cross(inst)
                inst.source_set(self)
                tmp.append(inst)
        # remove all handled instnaces from set
        for inst in tmp:
            TriggerHandler._wait_for_src.remove(inst)

    @staticmethod
    def _is_block_payload(data: list[Any]) -> bool:
        return bool(data) and isinstance(data[0], DNxscopeStreamBlock)

    def _alwaysoff(self, _: list[Any]) -> DTriggerState:
        # reset cache
        self._cache = []
        return DTriggerState(False, 0)

    def _alwayson(self, _: list[Any]) -> DTriggerState:
        return DTriggerState(True, 0)

    def _combined_vector_np(
        self, combined: list[Any], vect: int
    ) -> np.ndarray[Any, Any]:
        if not combined:
            return np.empty((0,), dtype=np.float64)

        if self._is_block_payload(combined):
            parts: list[np.ndarray[Any, Any]] = []
            for block in combined:
                parts.append(
                    np.asarray(block.data[:, vect], dtype=np.float64).reshape(
                        -1
                    )
                )
            if not parts:  # pragma: no cover
                return np.empty((0,), dtype=np.float64)
            if len(parts) == 1:
                return parts[0]
            return np.concatenate(parts)

        return np.fromiter(
            (float(sample.data[vect]) for sample in combined),
            dtype=np.float64,
            count=len(combined),
        )

    def _combined_vector(self, combined: list[Any], vect: int) -> list[float]:
        return [float(v) for v in self._combined_vector_np(combined, vect)]

    def _edgerising(
        self, combined: list[Any], vect: int, level: float
    ) -> DTriggerState:
        vec = self._combined_vector_np(combined, vect)
        if vec.size < 2:
            return DTriggerState(False, 0)
        hits = np.flatnonzero((vec[:-1] <= level) & (vec[1:] > level))
        if hits.size > 0:
            return DTriggerState(True, int(hits[0] + 1))
        return DTriggerState(False, 0)

    def _edgefalling(
        self, combined: list[Any], vect: int, level: float
    ) -> DTriggerState:
        vec = self._combined_vector_np(combined, vect)
        if vec.size < 2:
            return DTriggerState(False, 0)
        hits = np.flatnonzero((vec[:-1] >= level) & (vec[1:] < level))
        if hits.size > 0:
            return DTriggerState(True, int(hits[0] + 1))
        return DTriggerState(False, 0)

    def _windowenter(
        self, combined: list[Any], vect: int, low: float, high: float
    ) -> DTriggerState:
        vec = self._combined_vector_np(combined, vect)
        if vec.size < 2:
            return DTriggerState(False, 0)
        inside = (vec >= low) & (vec <= high)
        hits = np.flatnonzero((~inside[:-1]) & inside[1:])
        if hits.size > 0:
            return DTriggerState(True, int(hits[0] + 1))
        return DTriggerState(False, 0)

    def _windowexit(
        self, combined: list[Any], vect: int, low: float, high: float
    ) -> DTriggerState:
        vec = self._combined_vector_np(combined, vect)
        if vec.size < 2:
            return DTriggerState(False, 0)
        inside = (vec >= low) & (vec <= high)
        hits = np.flatnonzero(inside[:-1] & (~inside[1:]))
        if hits.size > 0:
            return DTriggerState(True, int(hits[0] + 1))
        return DTriggerState(False, 0)

    def _is_self_trigger(
        self, combined: list[Any], config: DTriggerConfig
    ) -> DTriggerState:
        if config.ttype is ETriggerType.ALWAYS_OFF:
            return self._alwaysoff(combined)
        elif config.ttype is ETriggerType.ALWAYS_ON:
            return self._alwayson(combined)
        elif config.ttype is ETriggerType.EDGE_RISING:
            assert config.level is not None
            return self._edgerising(combined, config.vect, config.level)
        elif config.ttype is ETriggerType.EDGE_FALLING:
            assert config.level is not None
            return self._edgefalling(combined, config.vect, config.level)
        elif config.ttype is ETriggerType.WINDOW_ENTER:
            assert config.window_low is not None
            assert config.window_high is not None
            return self._windowenter(
                combined,
                config.vect,
                config.window_low,
                config.window_high,
            )
        elif config.ttype is ETriggerType.WINDOW_EXIT:
            assert config.window_low is not None
            assert config.window_high is not None
            return self._windowexit(
                combined,
                config.vect,
                config.window_low,
                config.window_high,
            )
        else:
            raise AssertionError

    def _is_triggered(self, combined: list[Any]) -> DTriggerState:
        if self._trigger.state:
            # make sure that idx is 0
            return DTriggerState(True, 0)

        # cross-channel trigger
        if self._config.srcchan is not None:
            # source must be connected
            if not self._src_configured:
                raise AssertionError
            return self.cross_trigger

        # self-triggered
        return self._is_self_trigger(combined, self._config)

    def _cross_channel_handle(self, combined: list[Any]) -> None:
        for cross in self._cross:
            if cross.cross_trigger.state is True:
                continue
            # check cross channel requirements for trigger
            trigger = self._is_self_trigger(combined, cross.config)
            # signal if triggered
            if trigger.state is True:
                cross.cross_trigger = trigger

    @property
    def cross_trigger(self) -> DTriggerState:
        """Get cross tirgger state."""
        with self._lock:
            ret = deepcopy(self._cross_trigger)
        return ret

    @cross_trigger.setter
    def cross_trigger(self, val: DTriggerState) -> None:
        """Set cross tirgger state.

        :param val: cross triger state
        """
        with self._lock:
            self._cross_trigger = val

    @property
    def chan(self) -> int:
        """Get channel id associated with this trigger."""
        return self._chan

    @property
    def config(self) -> DTriggerConfig:
        """Get trigger configuration."""
        return self._config

    def pop_trigger_event(self) -> DTriggerEvent | None:
        """Return and clear the last emitted trigger event."""
        event = self._last_event
        self._last_event = None
        return event

    @classmethod
    def find_by_channel(cls, chan: int) -> "TriggerHandler | None":
        """Return registered trigger handler for one channel if present."""
        for inst in cls._instances:
            if inst.chan == chan:
                return inst
        return None

    @classmethod
    def cls_cleanup(cls: type["TriggerHandler"]) -> None:
        """Clean up all instances."""
        for x in cls._instances:
            x.cleanup(remove_self=False)
        # clear set
        cls._instances.clear()

    def cleanup(self, remove_self: bool = True) -> None:
        """Clean up instance."""
        if self._initdone:
            if self._src:
                self._src.unsubscribe_cross(self)
            if self in TriggerHandler._wait_for_src:
                TriggerHandler._wait_for_src.remove(self)
        else:  # pragma: no cover
            pass
        if remove_self:
            if self in self._instances:
                self._instances.remove(self)  # pragma: no cover

    def source_set(self, inst: "TriggerHandler") -> None:
        """Set source instance."""
        assert inst
        logger.info("set source trigger = %s for %s", str(inst), str(self))
        self._src = inst
        self._src_configured = True

    def subscribe_cross(self, inst: "TriggerHandler") -> None:
        """Subscribe as cross-channel trigger.

        :param inst: trigger handler instance to subscribe
        """
        self._cross.append(inst)

    def unsubscribe_cross(self, inst: "TriggerHandler") -> None:
        """Unsubscribe as cross-channel trigger.

        :param inst: trigger handler instance to unsubscribe
        """
        for i, cross in enumerate(self._cross):
            if cross is inst:  # pragma: no cover
                self._cross.pop(i)

    def _slice_from(self, combined: list[Any], start: int) -> list[Any]:
        if start <= 0:
            return combined
        if not combined:
            return []
        if not self._is_block_payload(combined):
            return combined[start:]

        ret: list[Any] = []
        offset = start
        for block in combined:
            rows = int(block.data.shape[0])
            if offset >= rows:
                offset -= rows
                continue
            if offset == 0:
                ret.append(block)
            else:
                data = block.data[offset:, :]
                meta = None if block.meta is None else block.meta[offset:, :]
                ret.append(DNxscopeStreamBlock(data=data, meta=meta))
            offset = 0
        return ret

    def _cache_tail(self, combined: list[Any], hoffset: int) -> list[Any]:
        if hoffset <= 0:
            return combined
        if not combined:
            return []
        if not self._is_block_payload(combined):
            return combined[-hoffset:]
        total = sum(int(block.data.shape[0]) for block in combined)
        start = max(total - hoffset, 0)
        return self._slice_from(combined, start)

    def _sample_count(self, combined: list[Any]) -> int:
        """Return number of samples in combined payload."""
        if not combined:
            return 0
        if not self._is_block_payload(combined):
            return len(combined)
        return sum(int(block.data.shape[0]) for block in combined)

    def _should_emit_event(self) -> bool:
        """Return ``True`` only for real trigger detections."""
        return self._config.ttype not in (
            ETriggerType.ALWAYS_ON,
            ETriggerType.ALWAYS_OFF,
        )

    def _slice_range(
        self, combined: list[Any], start: int, stop: int
    ) -> list[Any]:
        """Slice combined payload by sample range."""
        if stop <= start:
            return []
        if not combined:
            return []
        if not self._is_block_payload(combined):
            return combined[start:stop]

        ret: list[Any] = []
        offset = 0
        for block in combined:
            rows = int(block.data.shape[0])
            block_start = max(start - offset, 0)
            block_stop = min(stop - offset, rows)
            if block_stop > block_start:
                data = block.data[block_start:block_stop, :]
                meta = (
                    None
                    if block.meta is None
                    else block.meta[block_start:block_stop, :]
                )
                ret.append(DNxscopeStreamBlock(data=data, meta=meta))
            offset += rows
            if offset >= stop:
                break
        return ret

    def _tail_samples(self, combined: list[Any], count: int) -> list[Any]:
        """Keep only the last N samples for boundary detection."""
        if count <= 0:
            return []
        total = self._sample_count(combined)
        start = max(total - count, 0)
        return self._slice_range(combined, start, total)

    def _data_triggered_start_after(self, data: list[Any]) -> list[Any]:
        """Legacy start-after-trigger behavior with pre-trigger history."""
        combined = self._cache + data
        self._last_event = None

        self._trigger = self._is_triggered(combined)

        # check all cross-channel triggers
        self._cross_channel_handle(combined)

        pre_samples = self._config.effective_pre_samples

        if not self._trigger.state:
            ret = []
            if self._is_block_payload(combined):
                if pre_samples <= 0:
                    self._cache = data
                else:
                    self._cache = self._cache_tail(combined, pre_samples)
            else:
                clen = len(self._cache)
                self._cache = combined[clen - pre_samples :]
        else:
            first_trigger = not self._triger_done
            if not self._triger_done:
                hoffset = pre_samples
                self._triger_done = True
            else:
                hoffset = 0

            start_idx = self._trigger.idx - hoffset
            ret = self._slice_from(combined, start_idx)
            trigger_sample = self._trigger.idx - max(start_idx, 0)
            if first_trigger and self._should_emit_event():
                self._last_event = DTriggerEvent(
                    sample_index=float(trigger_sample),
                    channel=self._chan,
                    capture_mode=self._config.capture_mode,
                )
            self._cache = []

        return ret

    def _data_triggered_stop_after(self, data: list[Any]) -> list[Any]:
        """Stream immediately, then stop after trigger plus tail samples."""
        self._last_event = None
        if not self._should_emit_event():
            return data
        if not data and self._post_remaining <= 0:
            return []

        if not self._is_block_payload(data):
            raise NotImplementedError(
                "stop_after capture mode requires NumPy block stream payloads"
            )

        if self._trigger.state:
            total = self._sample_count(data)
            if self._post_remaining <= 0:
                return []
            returned = self._slice_range(
                data, 0, min(total, self._post_remaining)
            )
            self._post_remaining -= min(total, self._post_remaining)
            return returned

        combined = self._cache + data
        cache_rows = self._sample_count(self._cache)

        self._trigger = self._is_triggered(combined)
        self._cross_channel_handle(combined)

        if not self._trigger.state:
            self._cache = self._tail_samples(combined, 1)
            return data

        total = self._sample_count(combined)
        stop_at = self._trigger.idx + self._config.post_samples + 1
        returned = self._slice_range(combined, cache_rows, min(total, stop_at))
        self._last_event = DTriggerEvent(
            sample_index=max(
                self._trigger.idx - cache_rows,
                0.0,
            ),
            channel=self._chan,
            capture_mode=self._config.capture_mode,
        )
        self._post_remaining = max(stop_at - total, 0)
        self._cache = []
        return returned

    def data_triggered(self, data: list[Any]) -> list[Any]:
        """Get triggered data.

        :param data: stream data
        """
        if self._config.capture_mode is ETriggerCaptureMode.START_AFTER:
            return self._data_triggered_start_after(data)
        if self._config.capture_mode is ETriggerCaptureMode.STOP_AFTER:
            return self._data_triggered_stop_after(data)
        raise AssertionError
