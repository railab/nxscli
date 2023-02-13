import pytest  # type: ignore
from nxslib.comm import CommHandler
from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler
from nxslib.proto.parse import Parser

from nxscli.animation_mpl import IPluginAnimation
from nxscli.phandler import PluginHandler
from nxscli.plot_mpl import MplManager, PluginAnimationCommonMpl


class XTestAnimation(PluginAnimationCommonMpl):
    def __init__(self, fig, pdata, qdata, write):
        super().__init__(fig, pdata, qdata, write)

    def _animation_update(self, frame, pdata):  # pragma: no cover
        pass


class XTestPluginAnimation(IPluginAnimation):
    def __init__(self):
        super().__init__()

    def _start(self, fig, pdata, qdata, kwargs):
        return XTestAnimation(fig, pdata, qdata, kwargs["write"])


def test_ipluginanimation_init():
    # abstract class
    with pytest.raises(TypeError):
        IPluginAnimation()

    x = XTestPluginAnimation()

    # phandler not connected
    with pytest.raises(AttributeError):
        x.start(None)
    with pytest.raises(AttributeError):
        x.result()
    with pytest.raises(AttributeError):
        x.clear()
    with pytest.raises(AttributeError):
        x.stop()

    assert x.stream is True
    assert x.data_wait() is True

    phandler = PluginHandler()
    x.connect_phandler(phandler)


@pytest.fixture
def nxscope():
    intf = DummyDev()
    parse = Parser()
    comm = CommHandler(intf, parse)
    nxscope = NxscopeHandler()
    nxscope.intf_connect(comm)
    return nxscope


def test_ipluginanimation_start_nochannels(nxscope):
    MplManager.testctx(True)
    x = XTestPluginAnimation()
    p = PluginHandler()
    p.nxscope_connect(nxscope)
    x.connect_phandler(p)

    # start
    args = {"channels": [], "trig": [], "dpi": 100, "fmt": ""}
    assert x.start(args) is True

    # clear
    x.clear()

    # result
    x.result()

    # stop
    x.stop()


def test_ipluginanimation_start(nxscope):
    MplManager.testctx(True)
    x = XTestPluginAnimation()
    p = PluginHandler()
    p.nxscope_connect(nxscope)
    x.connect_phandler(p)

    # configure channels
    p.channels_configure([1], 0)

    # start
    args = {"channels": [1], "trig": [], "dpi": 100, "fmt": "", "write": False}
    assert x.start(args) is True

    # clear
    x.clear()

    # result
    x.result()

    # stop
    x.stop()
