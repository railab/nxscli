import json

import numpy as np
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.plugins.udp import PluginUdp


def test_pluginudp_init():
    plugin = PluginUdp()

    assert plugin.stream is True

    # TODO:


def test_pluginudp_handle_blocks_skips_empty_and_sends_json() -> None:
    class Sock:
        def __init__(self) -> None:
            self.sent: list[tuple[bytes, tuple[str, int]]] = []

        def sendto(self, payload: bytes, endpoint: tuple[str, int]) -> None:
            self.sent.append((payload, endpoint))

    plugin = PluginUdp()
    plugin._sock = Sock()
    plugin._address = "127.0.0.1"
    plugin._port = 1234
    plugin._data_format = "json"
    plugin._samples = 10
    plugin._nostop = False
    plugin._datalen = [0]
    pdata = type("Q", (), {"vdim": 1, "channame": "chan0"})()

    block0 = DNxscopeStreamBlock(data=np.empty((0, 1)), meta=None)
    block1 = DNxscopeStreamBlock(data=np.array([[3.0]]), meta=None)
    plugin._handle_blocks([block0, block1], pdata, 0)

    assert plugin._datalen == [1]
    assert len(plugin._sock.sent) == 1
    payload, endpoint = plugin._sock.sent[0]
    assert endpoint == ("127.0.0.1", 1234)
    decoded = json.loads(payload.decode())
    assert decoded["timestamp"] == 0
    assert decoded["chan0"] == 3.0
