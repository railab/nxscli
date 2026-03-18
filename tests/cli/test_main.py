import socket

import pytest  # type: ignore
from click.testing import CliRunner

import nxscli
from nxscli.cli.main import main
from tests.fake_nxscope import FakeNxscope


@pytest.fixture
def runner(mocker):
    mocker.patch.object(nxscli.cli.main, "wait_for_plugins", autospec=True)
    mocker.patch.object(
        nxscli.commands.interface.cmd_dummy,
        "NxscopeHandler",
        FakeNxscope,
    )
    return CliRunner()


def test_main(runner):
    result = runner.invoke(main)
    assert result.exit_code == 2


def test_main_dummy(runner):
    result = runner.invoke(main, ["dummy"])
    assert result.exit_code == 2


@pytest.mark.parametrize("_has_af_unix", [True, False])
def test_main_control_server_enabled(runner, monkeypatch, _has_af_unix):
    if _has_af_unix:
        monkeypatch.setattr(socket, "AF_UNIX", 1, raising=False)
    else:
        monkeypatch.delattr(socket, "AF_UNIX", raising=False)
    if hasattr(socket, "AF_UNIX"):
        endpoint = "unix-abstract://nxscli-test-control"
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            host, port = sock.getsockname()
        endpoint = f"tcp://{host}:{port}"

    args = [
        "--control-server",
        "--control-endpoint",
        endpoint,
        "dummy",
        "pdevinfo",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_control_server_enabled_init_failure(runner, monkeypatch):
    cleanup_called = {"flag": False}

    def fail_init(*_, **__):
        raise RuntimeError("boom")

    orig_cleanup = nxscli.cli.main.PluginHandler.cleanup

    def cleanup(self):
        cleanup_called["flag"] = True
        orig_cleanup(self)

    monkeypatch.setattr("nxscli.cli.main.ControlServerPlugin", fail_init)
    monkeypatch.setattr(
        "nxscli.cli.main.PluginHandler.cleanup", cleanup, raising=False
    )
    result = runner.invoke(
        main,
        [
            "--control-server",
            "--control-endpoint",
            "tcp://127.0.0.1:12345",
            "dummy",
            "pdevinfo",
        ],
    )
    assert result.exit_code != 0
    assert cleanup_called["flag"] is True


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


def test_main_pnpsave(runner):
    args = ["chan", "1", "pnpsave", "1", "./test"]
    result = runner.invoke(main, args)
    assert result.exit_code == 2

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


def test_main_vadd(runner):
    args = ["dummy", "vadd", "--operator", "scale_offset", "0", "0"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0


def test_main_vadd_pprinter_virtual_output(runner):
    args = [
        "dummy",
        "vadd",
        "--operator",
        "scale_offset",
        "--params",
        "scale=2,offset=1",
        "100",
        "0",
        "pprinter",
        "--chan",
        "v100",
        "3",
    ]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
    assert "virtual output v100 -> channel v100" in result.output
    assert "'chan': -1" in result.output
    assert "1:" in result.output


def test_main_udp_help(runner):
    args = ["udp", "--help"]
    result = runner.invoke(main, args)
    assert result.exit_code == 0
