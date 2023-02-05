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


def test_main_showinfo(runner):
    # test context not needed here
    Environment.testctx_set(False)
    result = runner.invoke(main, ["dummy", "showinfo"])
    assert result.exit_code == 0


def test_main_chan_nointf(runner):
    # test context not needed here
    Environment.testctx_set(False)

    result = runner.invoke(main, ["chan", "0"])
    assert result.exit_code == 2


def test_main_chan(runner):
    # test context not needed here
    Environment.testctx_set(False)

    result = runner.invoke(main, ["chan", "1000"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "chan", "1000"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "chan", "--divider", "1000", "1"])
    assert result.exit_code == 2

    result = runner.invoke(
        main, ["dummy", "chan", "--divider", "1000,1", "1,2"]
    )
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "chan", "0"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["dummy", "chan", "0,1"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["dummy", "chan", "all"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["dummy", "chan", "--divider", "1", "1"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["dummy", "chan", "--divider", "1,1", "0, 1"])
    assert result.exit_code == 0


def test_main_capture(runner):
    # test context needed
    Environment.testctx_set(True)

    result = runner.invoke(main, ["chan", "1", "capture", "1"])
    assert result.exit_code == 2

    # result = runner.invoke(main, ["dummy", "capture", "1"])
    # assert result.exit_code == 1

    result = runner.invoke(main, ["dummy", "chan", "1", "capture", "1"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["dummy", "chan", "1", "capture", "1000"])
    assert result.exit_code == 0


def test_main_csv(runner):
    # test context needed
    Environment.testctx_set(True)

    result = runner.invoke(main, ["chan", "1", "csv", "1", "./test"])
    assert result.exit_code == 2

    # result = runner.invoke(main, ["dummy", "csv", "1", "./test"])
    # assert result.exit_code == 1

    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["dummy", "chan", "1", "csv", "1", "./test"]
        )
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["dummy", "chan", "1", "csv", "1000", "./test"]
        )
        assert result.exit_code == 0

    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["dummy", "chan", "8", "csv", "--metastr", "1", "./test"]
        )
        assert result.exit_code == 0


def test_main_animation1(runner):
    # test context needed
    Environment.testctx_set(True)

    result = runner.invoke(main, ["chan", "1", "animation1"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "1", "animation1"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "chan", "1", "animation1"])
    assert result.exit_code == 0


def test_main_animation2(runner):
    # test context needed
    Environment.testctx_set(True)

    result = runner.invoke(main, ["chan", "1", "animation2", "1"])
    assert result.exit_code == 2

    # result = runner.invoke(main, ["dummy", "animation2", "1"])
    # assert result.exit_code == 1

    result = runner.invoke(main, ["dummy", "chan", "1", "animation2"])
    assert result.exit_code == 2

    result = runner.invoke(main, ["dummy", "chan", "1", "animation2", "1"])
    assert result.exit_code == 0
