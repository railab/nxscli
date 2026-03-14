"""Tests for virtual channel CLI command."""

from click.testing import CliRunner

from nxscli.channelref import ChannelRef
from nxscli.cli.environment import Environment
from nxscli.commands.config.cmd_vadd import cmd_vadd


class _FakeRuntime:
    def __init__(self) -> None:
        self.calls = []

    def add_virtual_channel(self, **kwargs):
        self.calls.append(kwargs)
        return [("v0", "v0")]


def test_cmd_vadd(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )

    env = Environment()
    env.phandler = object()
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["0", "0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert "channel v0" in result.output
    assert runtime.calls[0]["channel_id"] == 0


def test_cmd_vadd_requires_inputs(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    runner = CliRunner()
    result = runner.invoke(cmd_vadd, ["1"], obj=env)
    assert result.exit_code != 0


def test_cmd_vadd_sets_channels_from_physical_inputs(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["100", "0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert env.channels == ([ChannelRef.physical(0)], 0)


def test_cmd_vadd_merges_required_sources(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    env.channels = ([ChannelRef.physical(2)], 0)
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["100", "0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert env.channels == (
        [ChannelRef.physical(2), ChannelRef.physical(0)],
        0,
    )


def test_cmd_vadd_keeps_all_selector(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    env.channels = ([ChannelRef.all_channels()], 0)
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["100", "0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert env.channels == ([ChannelRef.all_channels()], 0)


def test_cmd_vadd_no_required_physical_sources(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["100", "v0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert env.channels is None


def test_cmd_vadd_does_not_duplicate_required_source(monkeypatch) -> None:
    runtime = _FakeRuntime()
    monkeypatch.setattr(
        "nxscli.commands.config.cmd_vadd.get_runtime",
        lambda _p: runtime,
    )
    env = Environment()
    env.phandler = object()
    env.channels = ([ChannelRef.physical(0)], 0)
    runner = CliRunner()
    result = runner.invoke(
        cmd_vadd,
        ["100", "0", "--operator", "scale_offset"],
        obj=env,
    )
    assert result.exit_code == 0
    assert env.channels == ([ChannelRef.physical(0)], 0)
