"""Module containing Numpy capture plugin."""

from typing import TYPE_CHECKING, Any

import click
import numpy as np

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options
from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.trigger import DTriggerConfigReq

###############################################################################
# Command: cmd_pnpsave
###############################################################################


@click.command(name="pnpsave")
@click.argument("samples", type=Samples(), required=True)
@click.argument("path", type=click.Path(resolve_path=False), required=True)
@capture_options
@pass_environment
def cmd_pnpsave(
    ctx: Environment,
    samples: int,
    path: str,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
) -> bool:
    """[plugin] Store samples in Numpy files.

    Each configured channel will be stored in a separate file.
    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "npsave",
        samples=samples,
        path=path,
        channels=chan,
        trig=trig,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Class: PluginNpsave
###############################################################################


class PluginNpsave(PluginThread, IPluginFile):
    """Plugin that capture data to Numpy file."""

    def __init__(self) -> None:
        """Intiialize a Numpy capture plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._path: str
        self._npdata: list[Any] = []

    def _init(self) -> None:
        assert self._phandler

        self._npdata = [[] for _ in range(len(self._data.qdlist))]
        for i, pdata in enumerate(self._data.qdlist):
            self._npdata[i] = [[] for v in range(pdata.vdim)]

    def _final(self) -> None:
        logger.info("numpy save captures DONE")

        for i, pdata in enumerate(self._data.qdlist):
            chanpath = self._path + "_chan" + str(pdata.chan) + ".npy"
            npdata = np.array(self._npdata[i])
            np.save(chanpath, npdata)

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        # store data
        for sample in data:
            for i in range(pdata.vdim):
                # TODO: metadata not supported for now
                self._npdata[j][i].append(sample.data[i])

        # get data len
        self._datalen[j] = len(self._npdata[j][0])

    def start(self, kwargs: Any) -> bool:
        """Start capture plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._path = kwargs["path"]
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
        """Get npsave plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
