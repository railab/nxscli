"""Module containing Nxscli stream data trigger logic."""

import itertools
from dataclasses import dataclass
from enum import Enum

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


class TriggerHandler:
    """The class used to handler stream data trigger."""

    def __init__(self, config: DTriggerConfig) -> None:
        """Initialize a stream data trigger handler."""
        self._config = config
        self._cache: list[tuple] = []

        self._trigger = False

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
        vect = 0
        for idx, data in enumerate(combined):
            # only the first item in vect checked for now
            if data[vect][0] == level:
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
        vect = 0
        for idx, data in enumerate(combined):
            # only the first item in vect checked for now
            if data[vect][0] == level:
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

    def _is_triggered(self, combined: list) -> tuple[bool, int]:
        if self._trigger:
            return True, 0

        trigger = self._config.ttype
        if trigger is ETriggerType.ALWAYS_OFF:
            return self._alwaysoff(combined)
        elif trigger is ETriggerType.ALWAYS_ON:
            return self._alwayson(combined)
        elif trigger is ETriggerType.EDGE_RISING:
            assert self._config.level is not None
            level = self._config.level
            return self._edgerising(combined, level)
        elif trigger is ETriggerType.EDGE_FALLING:
            assert self._config.level is not None
            level = self._config.level
            return self._edgefalling(combined, level)
        else:
            raise AssertionError

    def data_triggered(self, data: list) -> list:
        """Get triggered data.

        :param data: stream data
        """
        combined = self._cache + data
        self._trigger, idx = self._is_triggered(combined)

        if not self._trigger:
            # not triggered yet
            ret = []
            # update cache
            clen = len(self._cache)
            self._cache = combined[clen - self._config.hoffset :]
        else:
            # return data with a configured horisontal offset
            ret = combined[idx - self._config.hoffset :]
            # reset cache
            self._cache = []

        return ret
