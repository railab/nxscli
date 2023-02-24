import pytest  # type: ignore

from nxscli.iplugin import EPluginType, IPlugin


class XTestPlugin1(IPlugin):
    def __init__(self, ptype):
        super().__init__(ptype)

    @property
    def stream(self) -> bool:
        return False

    def stop(self):
        pass

    def data_wait(self):
        return True

    def start(self, ploter, kwargs):
        return True

    def result(self):
        return


def test_nxscliplugin_init():
    # abstract class
    with pytest.raises(TypeError):
        _ = IPlugin()

    # valid plugin type
    p1 = XTestPlugin1(EPluginType.TEXT)

    assert p1.ptype == EPluginType.TEXT
    assert p1.handled is False
    p1.handled = True
    assert p1.handled is True
    assert p1.stream is False

    # connect dummy handler
    p1.connect_phandler(None)

    p1.stop()
    p1.data_wait()
    p1.start(None, None)
    p1.result()

    # at default plugins dont need to wait
    assert p1.wait_for_plugin() is True
