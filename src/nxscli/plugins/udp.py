"""Module containing UDP plugin."""

import json
import socket
from typing import TYPE_CHECKING, Any

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread

if TYPE_CHECKING:
    from nxslib.nxscope import DNxscopeStream


###############################################################################
# Class: PluginUdp
###############################################################################


class PluginUdp(PluginThread, IPluginFile):
    """Plugin that stream data over UDP."""

    def __init__(self) -> None:
        """Initialize a UDP plugin."""
        IPluginFile.__init__(self)
        PluginThread.__init__(self)

        self._data: "PluginData"
        self._address: str
        self._port: int
        self._data_format: str
        self._sock: socket.socket

    def _init(self) -> None:
        assert self._phandler
        # open socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _final(self) -> None:
        self._sock.close()
        logger.info("UDP capture DONE")

    def _handle_samples(
        self, data: list["DNxscopeStream"], pdata: "PluginQueueData", j: int
    ) -> None:
        # store data
        for sample in data:
            if not self._nostop:  # pragma: no cover
                # ignore data if capture done for channel
                if self._datalen[j] >= self._samples:
                    break

            # get data
            temp: Any = {}
            temp["timestamp"] = self._datalen[j]

            # TODO: optimise
            for i, val in enumerate(sample.data):
                if pdata.vdim > 1:
                    s = pdata.channame + "_" + str(i)
                else:
                    s = pdata.channame

                temp[s] = val

            # encode data
            if self._data_format == "json":
                encoded = json.dumps(temp).encode()
            else:  # pragma: no cover
                raise ValueError("not supported data format")

            self._sock.sendto(encoded, (self._address, self._port))

            # one sample
            self._datalen[j] += 1

    def start(self, kwargs: Any) -> bool:
        """Start UDP plugin.

        :param kwargs: implementation specific arguments
        """
        assert self._phandler

        logger.info("start UDP %s", str(kwargs))

        self._samples = kwargs["samples"]
        self._port = kwargs["port"]
        self._address = kwargs["address"]
        self._data_format = kwargs["data_format"]
        self._nostop = kwargs["nostop"]

        if self._data_format not in ["json"]:  # pragma: no cover
            raise ValueError("not supported data format")

        chanlist = self._phandler.chanlist_plugin(kwargs["channels"])
        trig = self._phandler.triggers_plugin(chanlist, kwargs["trig"])

        cb = self._phandler.cb_get()
        self._data = PluginData(chanlist, trig, cb)

        if not self._data.qdlist:  # pragma: no cover
            return False

        self.thread_start(self._data)

        return True

    def result(self) -> None:
        """Get UDP plugin result."""
        # TODO: return file handler ?
        return  # pragma: no cover
