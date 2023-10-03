"""Default commands."""

from typing import TYPE_CHECKING

from nxscli.commands.cmd_csv import cmd_pcsv
from nxscli.commands.cmd_devinfo import cmd_pdevinfo
from nxscli.commands.cmd_none import cmd_pnone
from nxscli.commands.cmd_printer import cmd_printer
from nxscli.commands.cmd_udp import cmd_pudp
from nxscli.commands.config.cmd_chan import cmd_chan
from nxscli.commands.config.cmd_trig import cmd_trig

if TYPE_CHECKING:
    import click

commands_list: list["click.Command"] = [
    cmd_chan,
    cmd_trig,
    cmd_pdevinfo,
    cmd_pcsv,
    cmd_pnone,
    cmd_printer,
    cmd_pudp,
]
