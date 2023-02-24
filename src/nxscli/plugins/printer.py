"""Module containing printer plugin."""

import queue
from threading import Event
from typing import TYPE_CHECKING, Any

import click

from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import Samples, capture_options
from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginText
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream

    from nxscli.trigger import DTriggerConfigReq

###############################################################################
# Command: cmd_printer
###############################################################################


@click.command(name="pprinter")
@click.argument("samples", type=Samples(), required=True)
@capture_options
@click.option(
    "--metastr", default=False, is_flag=True, help="store metadata as string"
)
@pass_environment
def cmd_printer(
    ctx: Environment,
    samples: int,
    chan: list[int],
    trig: dict[int, "DTriggerConfigReq"],
    metastr: bool,
) -> bool:
    """[plugin] Print data from stream.

    If SAMPLES argument is set to 'i' then we capture data until enter
    is press.
    """  # noqa: D301
    # wait for enter if samples set to 'i'
    assert ctx.phandler
    if samples == 0:  # pragma: no cover
        ctx.waitenter = True

    ctx.phandler.enable(
        "printer",
        samples=samples,
        channels=chan,
        trig=trig,
        metastr=metastr,
        nostop=ctx.waitenter,
    )

    ctx.needchannels = True

    return True


###############################################################################
# Class: PluginPrinter
###############################################################################


class PluginPrinter(PluginThread, IPluginText):
    """Dummy plugin that print captured data."""

    def __init__(self) -> None:
        """Intiialize a printer plugin."""
        IPluginText.__init__(self)
        PluginThread.__init__(self)

        self._q: queue.Queue[Any] = queue.Queue()
        self._done = Event()
        self._ret_len = 0
        self._meta_string = False

        self._data: "PluginData"

    def _init(self) -> None:
        assert self._phandler

    def _final(self) -> None:
        logger.info("printer DONE")

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        for sample in data:
            if self._datalen[j] < self._samples:
                d: dict[str, Any] = dict()
                d["chan"] = self._data.qdlist[j].chan
                d["data"] = sample.data
                if self._meta_string:
                    d["meta"] = bytes(list(sample.meta)).decode()
                else:
                    d["meta"] = sample.meta
                self._q.put(d)
                self._datalen[j] += 1

    @property
    def handled(self) -> bool:
        """Get handled flag."""
        return self._handled

    @handled.setter
    def handled(self, val: bool) -> None:
        """Overload method common method.

        :param val: plugin handled state
        """
        if self._done.is_set():
            self._handled = val
        else:
            # force not handled
            self._handled = False

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """
        return True

    def start(self, kwargs: Any) -> bool:
        """Start printer plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start capture %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._meta_string = kwargs["metastr"]
        self._nostop = kwargs["nostop"]

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        cb = self._phandler.cb_get()
        self._data = PluginData(chanlist, trig, cb)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start(self._data)

        return True

    def result(self) -> str:
        """Get printer plugin result."""
        try:
            samples = self._q.get(block=True, timeout=1.0)
            self._ret_len += 1

        except queue.Empty:
            return ""

        if self._ret_len >= self._samples:
            self._done.set()

        s = str(self._ret_len) + ": " + str(samples)
        return s
