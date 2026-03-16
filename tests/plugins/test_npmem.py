import numpy as np

from nxscli.plugins.npmem import PluginNpmem


def test_pluginnpmem_init() -> None:
    plugin = PluginNpmem()
    assert plugin.stream is True


def test_pluginnpmem_handle_blocks_and_samples(tmp_path) -> None:
    class QData:
        def __init__(self) -> None:
            self.chan = 2
            self.vdim = 2

    class Data:
        def __init__(self) -> None:
            self.qdlist = [QData()]

    class Block:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    class Sample:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    plugin = PluginNpmem()
    plugin._phandler = object()
    plugin._data = Data()
    plugin._path = str(tmp_path / "capture")
    plugin._npshape = 2
    plugin._init()
    plugin._datalen = [0]
    pdata = plugin._data.qdlist[0]

    plugin._handle_samples([Sample((1.0, 2.0))], pdata, 0)
    assert plugin._datalen[0] == 0

    plugin._handle_blocks(
        [Block(np.array([[3.0, 4.0], [5.0, 6.0]]))], pdata, 0
    )
    assert plugin._datalen[0] == 2
    assert np.array_equal(
        np.asarray(plugin._npfiles[0]),
        np.array([[1.0, 3.0], [2.0, 4.0]], dtype=np.float32),
    )
