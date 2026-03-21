"""Module containing devinfo plugin."""

from typing import Any

from nxslib.dev import EDeviceChannelType
from rich import box
from rich.console import Console
from rich.table import Table

from nxscli.iplugin import IPluginText

###############################################################################
# Class: PluginDevinfo
###############################################################################


class PluginDevinfo(IPluginText):
    """Plugin that shows device information."""

    @staticmethod
    def _get_bool(data: dict[str, Any], key: str) -> bool:
        """Read a boolean-like field with a False default."""
        return bool(data.get(key, False))

    @staticmethod
    def _get_int(data: dict[str, Any], key: str) -> int:
        """Read an integer-like field with a zero default."""
        return int(data.get(key, 0))

    @staticmethod
    def _get_float(data: dict[str, Any], key: str) -> float:
        """Read a float-like field with a zero default."""
        return float(data.get(key, 0.0))

    @staticmethod
    def _format_bool(value: bool) -> str:
        """Return a short human-readable boolean."""
        return "yes" if value else "no"

    @staticmethod
    def _format_enabled(enabled: tuple[int, ...]) -> str:
        """Format enabled channel IDs as compact ranges."""
        if not enabled:
            return "none"

        ranges: list[str] = []
        start = enabled[0]
        end = enabled[0]

        for item in enabled[1:]:
            if item == end + 1:
                end = item
                continue

            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")

            start = item
            end = item

        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return ", ".join(ranges)

    @staticmethod
    def _render_channels_table(channels: list[dict[str, Any]]) -> str:
        """Render channels as a readable text table."""
        table = Table(box=box.ASCII_DOUBLE_HEAD, expand=False)

        table.add_column("ID", justify="right", no_wrap=True)
        table.add_column("Name", overflow="fold")
        table.add_column("Type", no_wrap=True)
        table.add_column("Dim", justify="right", no_wrap=True)
        table.add_column("Valid", no_wrap=True)
        table.add_column("En", no_wrap=True)
        table.add_column("Div", justify="right", no_wrap=True)

        for chan in channels:
            table.add_row(
                str(chan["chan"]),
                chan["name"] if chan["name"] else "-",
                chan["dtype_text"],
                str(chan["vdim"]),
                PluginDevinfo._format_bool(chan["valid"]),
                PluginDevinfo._format_bool(chan["enabled"]),
                str(chan["divider"]),
            )

        console = Console(
            force_terminal=False,
            color_system=None,
            width=100,
        )
        with console.capture() as capture:
            console.print(table)

        return capture.get()

    def __init__(self) -> None:
        """Initialize devinfo plugin."""
        super().__init__()
        self._return = None

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return False

    def stop(self) -> None:
        """Stop devinfo plugin."""

    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: not used
        """
        return True

    def start(self, _: Any) -> bool:
        """Start devinfo plugin."""
        assert self._phandler
        assert self._phandler.dev

        ret: Any = {}
        ret["cmn"] = vars(self._phandler.get_device_capabilities())
        ret["stream"] = vars(self._phandler.get_stream_stats())
        ret["channels_state_applied"] = vars(
            self._phandler.get_channels_state(applied=True)
        )
        ret["channels_state_buffered"] = vars(
            self._phandler.get_channels_state(applied=False)
        )

        tmp = []
        for chid in range(ret["cmn"]["chmax"]):
            chinfo = self._phandler.nxscope.dev_channel_get(chid)
            assert chinfo
            chan: Any = {}
            chan["chan"] = chinfo.data.chan
            chan["type"] = chinfo.data._type
            chan["dtype"] = chinfo.data.dtype
            chan["dtype_text"] = EDeviceChannelType.to_text(chinfo.data.dtype)
            chan["vdim"] = chinfo.data.vdim
            chan["name"] = chinfo.data.name
            chan["enabled"] = chinfo.data.en
            chan["valid"] = chinfo.data.is_valid
            chan["divider"] = self._phandler.get_channel_divider(chid)

            tmp.append(chan)

        ret["channels"] = tmp

        self._return = ret

        return True

    def result(self) -> str:
        """Get devinfo plugin result."""
        assert self._return
        cmn = self._return["cmn"]
        stream = self._return["stream"]
        applied = self._return["channels_state_applied"]
        buffered = self._return["channels_state_buffered"]
        channels = self._return["channels"]

        div_supported = self._get_bool(cmn, "div_supported")
        ack_supported = self._get_bool(cmn, "ack_supported")
        flags = self._get_int(cmn, "flags")
        rxpadding = self._get_int(cmn, "rxpadding")
        connected = self._get_bool(stream, "connected")
        stream_started = self._get_bool(stream, "stream_started")
        overflow_count = self._get_int(stream, "overflow_count")
        bitrate = self._get_float(stream, "bitrate")

        lines = [
            "",
            "Device Summary",
            f"  Channels:         {cmn['chmax']}",
            f"  Divider support:  {self._format_bool(div_supported)}",
            f"  Ack support:      {self._format_bool(ack_supported)}",
            f"  Flags:            0x{flags:02x}",
            f"  RX padding:       {rxpadding}",
            "",
            "Stream",
            f"  Connected:        {self._format_bool(connected)}",
            f"  Started:          {self._format_bool(stream_started)}",
            f"  Overflow count:   {overflow_count}",
            f"  Bitrate:          {bitrate:.1f} B/s",
            "",
            "Channel State",
            "  Applied enabled:  "
            f"{self._format_enabled(applied['enabled_channels'])}",
            "  Buffered enabled: "
            f"{self._format_enabled(buffered['enabled_channels'])}",
            "",
            "Channels",
        ]

        lines.append(self._render_channels_table(channels).rstrip("\n"))

        lines.append("")
        return "\n".join(lines)
