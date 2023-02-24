"""Module containint the Click environmet."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from nxslib.nxscope import NxscopeHandler
    from nxslib.proto.parse import Parser

    from nxscli.phandler import PluginHandler
    from nxscli.trigger import DTriggerConfigReq


###############################################################################
# Class: DEnvironmentData
###############################################################################


@dataclass
class DEnvironmentData:
    """Environment data."""

    debug: bool = False
    waitenter: bool = False
    nxscope: "NxscopeHandler | None" = None
    parser: "Parser | None" = None
    interface: bool = False
    needchannels: bool = False
    channels: tuple[list[int], Any] | None = None
    phandler: "PluginHandler | None" = None
    triggers: dict[int, "DTriggerConfigReq"] | None = None


###############################################################################
# Class: Environment
###############################################################################


class Environment(DEnvironmentData):
    """A class with application environmet."""

    def __init__(self) -> None:
        """Initialize environmet."""
        super().__init__()


###############################################################################
# Decorator: pass_environment
###############################################################################


# custom environmet decorator
pass_environment = click.make_pass_decorator(Environment, ensure=True)
