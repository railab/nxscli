"""Tests for virtual command parameter parsing."""

import click
import pytest

from nxscli.commands.config.cmd_vadd import _parse_params


def test_parse_params_ok() -> None:
    parsed = _parse_params(["a=1", "b=1.5", "c=true", "d=x", " "])
    assert parsed["a"] == 1
    assert parsed["b"] == 1.5
    assert parsed["c"] is True
    assert parsed["d"] == "x"


def test_parse_params_invalid() -> None:
    with pytest.raises(click.BadParameter):
        _parse_params(["broken"])

    with pytest.raises(click.BadParameter):
        _parse_params(["=1"])
