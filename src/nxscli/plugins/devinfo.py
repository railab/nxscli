"""Module containing devinfo plugin."""

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

    def start(self, _: dict) -> bool:
        """Start devinfo plugin."""
        assert self._phandler
        assert self._phandler.dev

        dev = self._phandler.dev

        ret: Any = {}
        ret["cmn"] = {}
        ret["cmn"]["chmax"] = dev.chmax
        ret["cmn"]["flags"] = dev.flags
        ret["cmn"]["rxpadding"] = dev.rxpadding

        tmp = []
        for chid in range(dev.chmax):
            chinfo = dev.channel_get(chid)
            assert chinfo
            chan: Any = {}
            chan["chan"] = chinfo.chan
            chan["type"] = chinfo._type
            chan["vdim"] = chinfo.vdim
            chan["name"] = chinfo.name

            tmp.append(chinfo)

        ret["channels"] = tmp  # type: ignore

        self._return = ret

        return True

    def result(self) -> dict | None:
        """Get devinfo plugin result."""
        return self._return
