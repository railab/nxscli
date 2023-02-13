"""Module containing Nxscli stream data trigger logic."""

import itertools
import weakref
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any

from nxscli.logger import logger

###############################################################################
# Enum: ETriggerType
###############################################################################


class ETriggerType(Enum):
    """Trigger types."""

    ALWAYS_OFF = 0
    ALWAYS_ON = 1
    EDGE_RISING = 2
    EDGE_FALLING = 3


###############################################################################
# Function: trigger_from_str
###############################################################################


def trigger_from_str(strg: list) -> "DTriggerConfig":
    """Get trigger configuration from string.

    :param strg: trigger configuration in string format
    """
    ttype = strg[0][0]
    srcchan = strg[0][1]
    if ttype == "off":
        # no arguments
        dtc = DTriggerConfig(ETriggerType.ALWAYS_OFF)
    elif ttype == "on":
        # no arguments
        dtc = DTriggerConfig(ETriggerType.ALWAYS_ON)
    elif ttype == "er":
        # argument 1 horisontal offset
        # argument 2 trigger level
        hoffset = int(strg[1])
        level = float(strg[2])
        dtc = DTriggerConfig(ETriggerType.EDGE_RISING, srcchan, hoffset, level)
    elif ttype == "ef":
        # argument 1 horisontal offset
        # argument 2 trigger level
        hoffset = int(strg[1])
        level = float(strg[2])
        dtc = DTriggerConfig(
            ETriggerType.EDGE_FALLING, srcchan, hoffset, level
        )
    else:
        raise AssertionError
    return dtc


###############################################################################
# Class: DTriggerConfig
###############################################################################


@dataclass
class DTriggerConfig:
    """Trigger configuration."""

    ttype: ETriggerType
    srcchan: int | None = None
    hoffset: int = 0
    level: float | None = None


###############################################################################
# Class: TriggerHandler
###############################################################################


class TriggerHandler(object):
    """The class used to handler stream data trigger."""

    _instances: weakref.WeakSet = weakref.WeakSet()
    _wait_for_src: weakref.WeakSet = weakref.WeakSet()

    def __new__(cls, *args: Any, **kwargs: Any) -> "TriggerHandler":
        """Create a new instance and store reference in a weak set."""
        instance = object.__new__(cls)
        cls._instances.add(instance)
        return instance

    def __init__(self, chan: int, config: DTriggerConfig) -> None:
        """Initialize a stream data trigger handler."""
        self._config = config
        self._cache: list[tuple] = []
        self._chan: int = chan
        self._trigger = False
        self._triger_done = False

        # trigger source channel reference
        self._src: "TriggerHandler" | None = None
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
        self._cross_trigger: tuple[bool, int] = (False, 0)

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

    def _pairwise(self, iterable: list) -> zip:
        (a, b) = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    def _alwaysoff(self, _: list) -> tuple[bool, int]:
        # reset cache
        self._cache = []
        return False, 0

    def _alwayson(self, _: list) -> tuple[bool, int]:
        return True, 0

    def _edgerising(self, combined: list, level: float) -> tuple[bool, int]:
        ret = False
        tmp = []
        vect = 0  # only the first item in vect checked for now
        for idx, data in enumerate(combined):
            if data[0][vect] == level:
                tmp.append(idx)

        for idx in tmp:
            if idx > 0:
                start = idx - 1
            else:
                # ignore if this is index 0
                continue

            ret = False
            for a, b in self._pairwise(combined[start:]):
                if a[vect] < b[vect]:
                    ret = True
                    break
            # found a risong edge on a given level
            if ret:
                break

        return ret, idx

    def _edgefalling(self, combined: list, level: float) -> tuple[bool, int]:
        ret = False
        tmp = []
        vect = 0  # only the first item in vect checked for now
        for idx, data in enumerate(combined):
            if data[0][vect] == level:
                tmp.append(idx)

        for idx in tmp:
            if idx > 0:
                start = idx - 1
            else:
                # ignore if this is index 0
                continue

            ret = False
            for a, b in self._pairwise(combined[start:]):
                if a[vect] > b[vect]:
                    ret = True
                    break
            # found a falling edge on a given level
            if ret:
                break

        return ret, idx

    def _is_self_trigger(
        self, combined: list, config: DTriggerConfig
    ) -> tuple[bool, int]:
        if config.ttype is ETriggerType.ALWAYS_OFF:
            return self._alwaysoff(combined)
        elif config.ttype is ETriggerType.ALWAYS_ON:
            return self._alwayson(combined)
        elif config.ttype is ETriggerType.EDGE_RISING:
            assert config.level is not None
            level = config.level
            return self._edgerising(combined, level)
        elif config.ttype is ETriggerType.EDGE_FALLING:
            assert config.level is not None
            level = config.level
            return self._edgefalling(combined, level)
        else:
            raise AssertionError

    def _is_triggered(self, combined: list) -> tuple[bool, int]:
        if self._trigger:
            return True, 0

        # cross-channel trigger
        if self._config.srcchan is not None:
            # source must be connected
            if not self._src_configured:
                raise AssertionError
            return self.cross_trigger

        # self-triggered
        return self._is_self_trigger(combined, self._config)

    def _cross_channel_handle(self, combined: list) -> None:
        for cross in self._cross:
            if cross.cross_trigger[0] is True:
                continue
            # check cross channel requirements for trigger
            trigger = self._is_self_trigger(combined, cross.config)
            # signal if triggered
            if trigger[0] is True:
                cross.cross_trigger = trigger

    @property
    def cross_trigger(self) -> tuple[bool, int]:
        """Get cross tirgger state."""
        with self._lock:
            ret = deepcopy(self._cross_trigger)
        return ret

    @cross_trigger.setter
    def cross_trigger(self, val: tuple[bool, int]) -> None:
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

    @classmethod
    def cls_cleanup(cls: type["TriggerHandler"]) -> None:
        """Clean up all instances."""
        for x in cls._instances:
            x.cleanup()

    def cleanup(self) -> None:
        """Clean up instance."""
        if self._src:
            self._src.unsubscribe_cross(self)
        if self in TriggerHandler._wait_for_src:
            TriggerHandler._wait_for_src.remove(self)

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

    def data_triggered(self, data: list) -> list:
        """Get triggered data.

        :param data: stream data
        """
        combined = self._cache + data
        self._trigger, idx = self._is_triggered(combined)

        # check all cross-channel triggers
        self._cross_channel_handle(combined)

        if not self._trigger:
            # not triggered yet
            ret = []
            # update cache
            clen = len(self._cache)
            self._cache = combined[clen - self._config.hoffset :]
        else:
            # one time hoffset for trigger
            if not self._triger_done:
                hoffset = self._config.hoffset
                self._triger_done = True
            else:
                hoffset = 0

            # return data with a configured horisontal offset
            ret = combined[idx - hoffset :]
            # reset cache
            self._cache = []

        return ret
