"""Module containing devinfo plugin."""

import pprint
from typing import Any

from nxscli.iplugin import IPluginText

###############################################################################
# Class: PluginDevinfo
###############################################################################


class PluginDevinfo(IPluginText):
    """Plugin that shows device information."""

    def __init__(self) -> None:
        """Initialize devinfo plugin."""
        super().__init__()
        self._return = None

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return False

    def stop(self) -> None:
        """Stop devinfo plugin."""

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: not used
        """
        return True

    def start(self, _: Any) -> bool:
        """Start devinfo plugin."""
        assert self._phandler
        assert self._phandler.dev

        dev = self._phandler.dev

        ret: Any = {}
        ret["cmn"] = {}
        ret["cmn"]["chmax"] = dev.data.chmax
        ret["cmn"]["flags"] = dev.data.flags
        ret["cmn"]["rxpadding"] = dev.data.rxpadding

        tmp = []
        for chid in range(dev.data.chmax):
            chinfo = dev.channel_get(chid)
            assert chinfo
            chan: Any = {}
            chan["chan"] = chinfo.data.chan
            chan["type"] = chinfo.data._type
            chan["vdim"] = chinfo.data.vdim
            chan["name"] = chinfo.data.name

            tmp.append(chan)

        ret["channels"] = tmp

        self._return = ret

        return True

    def result(self) -> str:
        """Get devinfo plugin result."""
        assert self._return
        s = "\nDevice common:\n"
        s += pprint.pformat(self._return["cmn"])
        s += "\nDevice channels:\n"
        s += pprint.pformat(self._return["channels"])
        s += "\n"
        return s
