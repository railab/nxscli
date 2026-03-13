import numpy as np
import pytest
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.pluginthr import PluginThread


class _ThreadStub:
    def __init__(self) -> None:
        self.stopped = False

    def stop_set(self) -> None:
        self.stopped = True


class _PluginThreadImpl(PluginThread):
    def __init__(self) -> None:
        super().__init__()
        self.handled: list[object] = []

    def _handle_blocks(self, data, pdata, j) -> None:  # noqa: ANN001
        self.handled.extend(data)
        self._datalen[j] += len(data)

    def _init(self) -> None:  # pragma: no cover
        return

    def _final(self) -> None:  # pragma: no cover
        return


def test_pluginthread_block_payload_uses_queue_get() -> None:
    class PData:
        def queue_get(
            self, block: bool = True, timeout: float = 1.0
        ):  # noqa: ANN001, ARG002
            return [DNxscopeStreamBlock(data=np.array([[1.0]]), meta=None)]

    plug = _PluginThreadImpl()
    plug._thread = _ThreadStub()
    plug._plugindata = type("PD", (), {"qdlist": [PData()]})()
    plug._samples = 1
    plug._nostop = False
    plug._datalen = [0]

    plug._thread_common()

    assert len(plug.handled) == 1
    assert plug._datalen == [1]
    assert plug._thread.stopped is True


def test_pluginthread_block_payload_without_converter_uses_queue_get() -> None:
    class PData:
        def queue_get(
            self, block: bool = True, timeout: float = 1.0
        ):  # noqa: ANN001, ARG002
            return [DNxscopeStreamBlock(data=np.array([[1.0]]), meta=None)]

    plug = _PluginThreadImpl()
    plug._thread = _ThreadStub()
    plug._plugindata = type("PD", (), {"qdlist": [PData()]})()
    plug._samples = 1
    plug._nostop = False
    plug._datalen = [0]

    plug._thread_common()

    assert len(plug.handled) == 1
    assert plug._datalen == [1]
    assert plug._thread.stopped is True


def test_pluginthread_block_rows_handles_none_meta() -> None:
    class _PData:
        pass

    plug = _PluginThreadImpl()
    rows = list(
        plug._block_rows(
            [DNxscopeStreamBlock(data=np.array([[1.0], [2.0]]), meta=None)],
            _PData(),
            0,
        )
    )
    assert rows == [((1.0,), ()), ((2.0,), ())]


def test_pluginthread_non_block_payload_raises() -> None:
    class PData:
        def queue_get(
            self, block: bool = True, timeout: float = 1.0
        ):  # noqa: ANN001, ARG002
            return [{"data": [1.0]}]

    plug = _PluginThreadImpl()
    plug._thread = _ThreadStub()
    plug._plugindata = type("PD", (), {"qdlist": [PData()]})()
    plug._samples = 1
    plug._nostop = False
    plug._datalen = [0]

    with pytest.raises(RuntimeError):
        plug._thread_common()


def test_pluginthread_empty_payload_is_ignored() -> None:
    class PData:
        def queue_get(
            self, block: bool = True, timeout: float = 1.0
        ):  # noqa: ANN001, ARG002
            return []

    plug = _PluginThreadImpl()
    plug._thread = _ThreadStub()
    plug._plugindata = type("PD", (), {"qdlist": [PData()]})()
    plug._samples = 1
    plug._nostop = False
    plug._datalen = [0]

    plug._thread_common()

    assert plug.handled == []
    assert plug._datalen == [0]
