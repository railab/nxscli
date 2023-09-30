"""Default interfaces."""

from typing import TYPE_CHECKING

from nxscli.commands.interface.cmd_dummy import cmd_dummy
from nxscli.commands.interface.cmd_rtt import cmd_rtt
from nxscli.commands.interface.cmd_serial import cmd_serial

if TYPE_CHECKING:
    import click

interfaces_list: list["click.Group"] = [cmd_serial, cmd_rtt, cmd_dummy]
