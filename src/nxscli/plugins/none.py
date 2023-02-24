"""Module containing dummy capture plugin."""

from typing import TYPE_CHECKING, Any

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginNone
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream


###############################################################################
# Class: PluginNone
###############################################################################


class PluginNone(PluginThread, IPluginNone):
    """Dummy plugin that do nothing with captured data."""

    def __init__(self) -> None:
        """Intiialize a none plugin."""
        IPluginNone.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"

    def _init(self) -> None:
        assert self._phandler

    def _final(self) -> None:
        logger.info("None DONE")

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        for _ in data:
            # get data len
            self._datalen[j] += 1

    def start(self, kwargs: Any) -> bool:
        """Start none plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._nostop = kwargs["nostop"]

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        cb = self._phandler.cb_get()
        self._data = PluginData(chanlist, trig, cb)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start(self._data)

        return True

    def result(self) -> None:
        """Get none plugin result."""
        return  # pragma: no cover
