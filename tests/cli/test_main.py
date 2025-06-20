import pytest  # type: ignore
from click.testing import CliRunner

import nxscli
from nxscli.cli.main import main


@pytest.fixture
def runner(mocker):
    mocker.patch.object(nxscli.cli.main, "wait_for_plugins", autospec=True)
    return CliRunner()


def test_main(runner):
    result = runner.invoke(main)
    assert result.exit_code == 2


def test_main_dummy(runner):
    result = runner.invoke(main, ["dummy"])
    assert result.exit_code == 2


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


def test_main_pprinter(runner):
    args = ["chan", "1", "pprinter", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pprinter", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pprinter", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "9", "pprinter", "--metastr", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "pprinter", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pudp(runner):
    args = ["chan", "1", "pudp", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pudp", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pudp", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "9", "pudp", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "pudp", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_trig(runner):
    args = ["dummy", "chan", "1", "trig", "xxx"]
    result = runner.invoke(main, args)
    assert result.exit_code == 1

    args = ["dummy", "chan", "1", "trig", "1:er,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1:er#2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1:er@2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1:er#1@2,0,100"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "trig", "1:er@2#2,0,100"]
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
