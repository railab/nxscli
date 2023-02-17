from unittest.mock import Mock

import pytest  # type: ignore
from click.testing import CliRunner

import nxscli
from nxscli.main.main import get_list_from_str, get_list_from_str2, main


class FigureMock:  # pragma: no cover
    def __init__(self):
        self.canvas = Mock()
        self.number = 0

    def delaxes(self, ax):
        pass

    def add_subplot(self, row, col, i):
        return AxesMock()


class AxesMock:  # pragma: no cover
    def __init__(self):
        pass

    def plot(self, arg1, arg2=None, arg3=None):
        return (Mock(),)

    def get_xlim(self):
        pass

    def get_ylim(self):
        pass

    def set_xlim(self, a, b):
        pass

    def set_ylim(self, a, b):
        pass

    def get_title(self):
        pass

    def set_title(self, a1):
        pass

    def get_xaxis(self):
        pass

    def grid(self, a1):
        pass


class MplManagerMock:  # pragma: no cover
    @staticmethod
    def draw():
        pass

    @staticmethod
    def fig_is_open():
        pass

    @staticmethod
    def pause(interval):
        pass

    @classmethod
    def show(cls, block):
        pass

    @staticmethod
    def mpl_config():
        pass

    @staticmethod
    def figure(dpi: float = 100.0):
        return FigureMock()

    def func_animation(**kwargs):
        return Mock()

    @staticmethod
    def close(fig):
        pass


def test_get_list_from_str():
    assert get_list_from_str("") == []
    assert get_list_from_str("a,b") == ["a", "b"]
    assert get_list_from_str("a+a", char="+") == ["a", "a"]
    assert get_list_from_str("ala,ala,bala") == ["ala", "ala", "bala"]

    assert get_list_from_str2("") == []
    assert get_list_from_str2("a,b,c,d") == [["a", "b", "c", "d"]]
    assert get_list_from_str2("a,b;c,d") == [["a", "b"], ["c", "d"]]


@pytest.fixture
def runner(mocker):
    mocker.patch.object(nxscli.main.main, "wait_for_plugins", autospec=True)
    mocker.patch.object(nxscli.plot_mpl, "MplManager", MplManagerMock)
    return CliRunner()


def test_main(runner):
    result = runner.invoke(main)
    assert result.exit_code == 0


def test_main_dummy(runner):
    result = runner.invoke(main, ["dummy"])
    assert result.exit_code == 0


def test_main_pdevinfo(runner):
    args = ["dummy", "pdevinfo"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_chan_nointf(runner):
    args = ["chan", "0"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2


def test_main_chan(runner):
    args = ["chan", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "--divider", "1000", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "--divider", "1000,1", "1,2"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "0"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "0,1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "all"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "--divider", "1", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "--divider", "1,1", "0, 1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pcap(runner):
    args = ["chan", "1", "pcap", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pcap", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pcap", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "pcap", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pcsv(runner):
    args = ["chan", "1", "pcsv", "1", "./test"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pcsv", "1", "./test"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pcsv", "1", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pcsv", "1000", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "8", "pcsv", "--metastr", "1", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0


def test_main_pnpsave(runner):
    args = ["chan", "1", "pnpsave", "1", "./test"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pnpsave", "1", "./test"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pnpsave", "1", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pnpsave", "1000", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "5", "pnpsave", "1", "./test"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0


def test_main_pnpmem(runner):
    args = ["chan", "1", "pnpmem", "1", "./test", "100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pnpmem", "1", "./test"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pnpmem", "10", "./test", "100"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "1", "pnpmem", "10", "./test", "100"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        args = ["dummy", "chan", "5", "pnpmem", "400", "./test", "200"]
        result = runner.invoke(main, args)
        assert result.exit_code == 0


def test_main_pani1(runner):
    args = ["chan", "1", "pani1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "1", "pani1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "pani1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pani2(runner):
    args = ["chan", "1", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pani2", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pani2"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pnone(runner):
    args = ["chan", "1", "pnone", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pnone", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pnone", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "pnone", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_trig(runner):
    args = ["dummy", "chan", "1", "trig", "xxx"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "1=er,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1=er#2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1=er@2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1=er#1@2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1=er@2#2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_trig_plugin(runner):
    args = ["dummy", "chan", "1", "trig", "xxx", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "x=1", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "g:1", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "g=on", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "g=off", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1,2", "trig", "1=on;2=off", "pani2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1,2,3", "pani2", "--trig", "2=off", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_help(runner):
    args = ["dummy", "--help"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "--help"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "trig", "--help"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
