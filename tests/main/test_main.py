import pytest  # type: ignore
from click.testing import CliRunner

from nxscli.main.main import Environment, main


@pytest.fixture
def runner():
    return CliRunner()


def test_main(runner):
    result = runner.invoke(main)
    assert result.exit_code == 0


def test_main_dummy(runner):
    result = runner.invoke(main, ["dummy"])
    assert result.exit_code == 0


def test_main_pdevinfo(runner):
    # test context not needed here
    Environment.testctx_set(False)

    args = ["dummy", "pdevinfo"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_chan_nointf(runner):
    # test context not needed here
    Environment.testctx_set(False)

    args = ["chan", "0"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2


def test_main_chan(runner):
    # test context not needed here
    Environment.testctx_set(False)

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


def test_main_pcapture(runner):
    # test context needed
    Environment.testctx_set(True)

    args = ["chan", "1", "pcapture", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "pcapture", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "pcapture", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0

    args = ["dummy", "chan", "1", "pcapture", "1000"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_pcsv(runner):
    # test context needed
    Environment.testctx_set(True)

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


def test_main_panimation1(runner):
    # test context needed
    Environment.testctx_set(True)

    args = ["chan", "1", "panimation1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "1", "panimation1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "panimation1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_panimation2(runner):
    # test context needed
    Environment.testctx_set(True)

    args = ["chan", "1", "panimation2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    # args = ["dummy", "panimation2", "1"]
    # result = runner.invoke(main, args)
    # assert result.exit_code == 1

    args = ["dummy", "chan", "1", "panimation2"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

    args = ["dummy", "chan", "1", "panimation2", "1"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
