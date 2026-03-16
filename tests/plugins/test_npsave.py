import numpy as np

from nxscli.plugins.npsave import PluginNpsave


def test_pluginnpsave_init() -> None:
    plugin = PluginNpsave()
    assert plugin.stream is True


def test_pluginnpsave_handle_blocks_and_final(tmp_path) -> None:
    class QData:
        def __init__(self) -> None:
            self.chan = 1
            self.vdim = 2

    class Data:
        def __init__(self) -> None:
            self.qdlist = [QData()]

    class Block:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    plugin = PluginNpsave()
    plugin._phandler = object()
    plugin._data = Data()
    plugin._path = str(tmp_path / "capture")
    plugin._init()
    plugin._datalen = [0]

    pdata = plugin._data.qdlist[0]
    plugin._handle_blocks(
        [Block(np.array([[1.0, 2.0], [3.0, 4.0]]))], pdata, 0
    )
    plugin._final()

    arr = np.load(str(tmp_path / "capture_chan1.npy"))
    assert arr.shape == (2, 2)
    assert np.array_equal(arr, np.array([[1.0, 3.0], [2.0, 4.0]]))
    assert plugin._datalen[0] == 2


def test_pluginnpsave_handle_samples() -> None:
    class QData:
        def __init__(self) -> None:
            self.chan = 1
            self.vdim = 2

    class Data:
        def __init__(self) -> None:
            self.qdlist = [QData()]

    class Sample:
        def __init__(self, data):  # noqa: ANN001
            self.data = data

    plugin = PluginNpsave()
    plugin._phandler = object()
    plugin._data = Data()
    plugin._init()
    plugin._datalen = [0]
    pdata = plugin._data.qdlist[0]
    plugin._handle_samples([Sample((1.0, 2.0)), Sample((3.0, 4.0))], pdata, 0)
    assert plugin._datalen[0] == 2


def test_pluginnpsave_final_empty_chunks(tmp_path) -> None:
    class QData:
        def __init__(self) -> None:
            self.chan = 3
            self.vdim = 2

    class Data:
        def __init__(self) -> None:
            self.qdlist = [QData()]

    plugin = PluginNpsave()
    plugin._phandler = object()
    plugin._data = Data()
    plugin._path = str(tmp_path / "capture_empty")
    plugin._init()
    plugin._final()
    arr = np.load(str(tmp_path / "capture_empty_chan3.npy"))
    assert arr.shape == (2, 0)
