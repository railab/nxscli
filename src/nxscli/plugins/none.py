"""Module containing Numpy capture plugin."""

from typing import TYPE_CHECKING, Any

import click

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginNone
from nxscli.logger import logger
from nxscli.main.environment import Environment, pass_environment
from nxscli.main.types import Samples, capture_options
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.trigger import DTriggerConfigReq

###############################################################################
# Command: cmd_pnone
###############################################################################


@click.command(name="pnone")
@click.argument("samples", type=Samples(), required=True)
@capture_options
@pass_environment
def cmd_pnone(
    ctx: Environment,
    samples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
) -> bool:
    """[plugin] Capture data and do nothing with them.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "none",
        samples=samples,
        channels=chan,
        trig=trig,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


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
