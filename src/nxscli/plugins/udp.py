"""Module containing UDP plugin."""

import json
import socket
from typing import Any

import numpy as np

from nxscli.idata import PluginData, PluginQueueData
from nxscli.iplugin import IPluginFile
from nxscli.logger import logger
from nxscli.pluginthr import PluginThread, StreamBlocks

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

    def _handle_blocks(
        self, data: StreamBlocks, pdata: "PluginQueueData", j: int
    ) -> None:
        if pdata.vdim > 1:
            keys = [pdata.channame + "_" + str(i) for i in range(pdata.vdim)]
        else:
            keys = [pdata.channame]

        dumps = json.dumps
        sendto = self._sock.sendto
        endpoint = (self._address, self._port)

        for block in data:
            block_data = block.data
            assert isinstance(block_data, np.ndarray)
            rows = int(block_data.shape[0])
            if rows == 0:
                continue

            if not self._nostop:  # pragma: no cover
                remaining = self._samples - self._datalen[j]
                if remaining <= 0:
                    break
                rows = min(rows, remaining)
                if rows <= 0:  # pragma: no cover
                    break

            start = self._datalen[j]
            for offs, row in enumerate(block_data[:rows]):
                temp: dict[str, Any] = {"timestamp": start + offs}
                for key, val in zip(keys, row):
                    temp[key] = float(val)

                # encode data
                if self._data_format == "json":
                    encoded = dumps(temp).encode()
                else:  # pragma: no cover
                    raise ValueError("not supported data format")

                sendto(encoded, endpoint)

            self._datalen[j] += rows

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
