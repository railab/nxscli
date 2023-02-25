"""Module containing the Click types."""

from typing import Any

import click

from nxscli.trigger import DTriggerConfigReq

###############################################################################
# Function: get_list_from_str
###############################################################################


def get_list_from_str(value: str, char: str = ",") -> list[str]:
    """Get list of values from string argument."""
    if not len(value):
        return []
    # remove white spaces
    tmp = value.replace(" ", "")
    # one separator
    return tmp.split(char)


###############################################################################
# Function: get_list_from_str2
###############################################################################


def get_list_from_str2(
    value: str, char1: str = ",", char2: str = ";"
) -> list[list[str]]:
    """Get list of values from string argument."""
    if not len(value):
        return []
    # remove white spaces
    tmp = value.replace(" ", "")

    # two separators, start from the second one
    ch2 = tmp.split(char2)
    ch1 = []
    for ch in ch2:
        ch1.append(ch.split(char1))
    return ch1


###############################################################################
# Class: Channels
###############################################################################


class Channels(click.ParamType):
    """Parse channels argument."""

    name = "channels"

    def convert(self, value: Any, param: Any, ctx: Any) -> list[int]:
        """Convert channels argument."""
        lint = []
        if value == "all":
            # special case to indicate all channels
            lint.append(-1)
            return lint

        lstr = get_list_from_str(value)
        for ch in lstr:
            assert ch.isnumeric(), "channel id must be a valid integer"
            chan = int(ch)
            if chan < 0 or chan > 255:
                raise click.BadParameter(
                    "channel id must be in range [0, 255]"
                )
            lint.append(chan)

        return lint


###############################################################################
# Class: Samples
###############################################################################


class Samples(click.ParamType):
    """Parse samples argument."""

    name = "samples"

    def convert(self, value: Any, param: Any, ctx: Any) -> int:
        """Convert samples argument."""
        if value.isnumeric():
            return int(value)
        elif value == "i":
            return -1
        else:
            raise click.BadParameter("samples must be a valid integer or 'i'")


###############################################################################
# Class: Trigger
###############################################################################


class Trigger(click.ParamType):
    """Parse trigger argument."""

    name = "trigger"

    req_split = ";"
    req_assign = ":"
    req_separator = ","
    req_cross = "#"
    req_global = "g"
    req_vect = "@"

    def convert(
        self, value: Any, param: Any, ctx: Any
    ) -> dict[int, DTriggerConfigReq]:
        """Convert trigger argument."""
        tmp = get_list_from_str(value, self.req_split)
        # get configurations
        ret = {}
        for trg in tmp:
            schan, params = trg.split(self.req_assign)
            tmp = params.split(self.req_separator)

            # decore trigger cross channel and channel vector
            vect_idx = tmp[0].find(self.req_vect)
            cross_idx = tmp[0].find(self.req_cross)
            if vect_idx != -1 and cross_idx != -1:
                if vect_idx > cross_idx:
                    trg = tmp[0][:cross_idx]
                    cross = int(tmp[0][cross_idx + 1 : vect_idx])
                    vect = int(tmp[0][vect_idx + 1 :])
                else:
                    trg = tmp[0][:vect_idx]
                    vect = int(tmp[0][vect_idx + 1 : cross_idx])
                    cross = int(tmp[0][cross_idx + 1 :])
            elif vect_idx == -1 and cross_idx != -1:
                trg, cross_s = tmp[0].split(self.req_cross)
                cross = int(cross_s)
                vect = 0
            elif vect_idx != -1 and cross_idx == -1:
                trg, vect_s = tmp[0].split(self.req_vect)
                vect = int(vect_s)
                cross = None
            else:
                trg = tmp[0]
                vect = 0
                cross = None

            cfg = tmp[1:]
            # special case for global configuration
            if schan == self.req_global:
                chan = -1
            else:
                chan = int(schan)

            # reset cross source if we point to ourself
            if cross == chan:
                cross = None

            req = DTriggerConfigReq(trg, cross, vect, cfg)
            ret[chan] = req
        return ret


###############################################################################
# Class: Divider
###############################################################################


class Divider(click.ParamType):
    """Parse divider argument."""

    name = "divider"

    def convert(self, value: Any, param: Any, ctx: Any) -> list[int] | int:
        """Convert divider argument."""
        lstr = get_list_from_str(value)
        lint = []
        for d in lstr:
            assert d.isnumeric(), "divider must be a valid integer"
            div = int(d)
            if div < 0 or div > 255:
                raise click.BadParameter("divnel id must be in range [0, 255]")
            lint.append(div)

        # return as int if one element
        if len(lint) == 1:
            return lint[0]
        # else return list
        return lint


###############################################################################
# Class: StringList
###############################################################################


class StringList(click.ParamType):
    """Parse a string list argument."""

    name = "stringlist"

    def __init__(self, ch1: str = ",") -> None:
        """Initialize parser."""
        super().__init__()
        self._ch1 = ch1

    def convert(self, value: Any, param: Any, ctx: Any) -> list[str]:
        """Convert a string list argument."""
        return get_list_from_str(value, self._ch1)


###############################################################################
# Class: StringList2
###############################################################################


class StringList2(click.ParamType):  # pragma: no cover
    """Parse a string list argument (2 separators)."""

    name = "stringlist2"

    def __init__(self, ch1: str = ",", ch2: str = ";") -> None:
        """Initialize parser."""
        super().__init__()
        self._ch1 = ch1
        self._ch2 = ch2

    def convert(self, value: Any, param: Any, ctx: Any) -> list[list[str]]:
        """Convert a string list argument."""
        return get_list_from_str2(value, self._ch1, self._ch2)


###############################################################################
# Globals: stirngs
###############################################################################


channels_option_help = """Plugin specific channels configuration,
                           for details look at 'chan' command"""  # noqa: D301
trigger_option_help = """Plugin specific triggers configuration,
                          for details look at 'tirg' command"""  # noqa: D301
divider_option_help = """Configure divider for a given channels.
                          Use a single integer to configure all channels with
                          the same divider value, or use a list of integers
                          (separated by commas) to directly configure the
                          channels."""


###############################################################################
# Decorator: capture_options
###############################################################################


# common capture options
_capture_options = (
    click.option(
        "--chan",
        default=None,
        type=Channels(),
        help=channels_option_help,
    ),
    click.option(
        "--trig",
        default=None,
        type=Trigger(),
        help=trigger_option_help,
    ),
)


def capture_options(fn: Any) -> Any:
    """Decorate command with common capture options decorator."""
    for decorator in reversed(_capture_options):
        fn = decorator(fn)
    return fn
