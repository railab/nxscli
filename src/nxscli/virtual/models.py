"""Data models for virtual channels."""

from dataclasses import dataclass, field

from nxslib.dev import DeviceChannel, EDeviceChannelType


@dataclass(frozen=True)
class ChannelSpec:
    """Channel metadata used by the virtual-channel graph."""

    channel_id: str
    name: str
    dtype: int
    vdim: int
    data_kind: str = "timeseries"
    device_channel: DeviceChannel = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Back this spec with nxslib ``DeviceChannel``."""
        dtype = _to_dtype_code(self.dtype)
        object.__setattr__(self, "dtype", dtype)
        object.__setattr__(
            self,
            "device_channel",
            DeviceChannel(
                chan=_parse_channel_number(self.channel_id),
                _type=dtype,
                vdim=self.vdim,
                name=self.name,
            ),
        )

    @classmethod
    def from_device_channel(
        cls,
        channel: DeviceChannel,
        channel_id: str | None = None,
        data_kind: str = "timeseries",
    ) -> "ChannelSpec":
        """Create spec from an existing nxslib ``DeviceChannel``."""
        return cls(
            channel_id=channel_id or str(channel.data.chan),
            name=channel.data.name,
            dtype=channel.data.dtype,
            vdim=channel.data.vdim,
            data_kind=data_kind,
        )


@dataclass(frozen=True)
class VirtualChannelSpec:
    """Virtual channel declaration."""

    channel_id: str
    name: str
    operator: str
    inputs: tuple[str, ...]
    params: dict[str, object] = field(default_factory=dict)
    enabled: bool = True


SampleValue = tuple[float, ...]


def to_float(value: object, fallback: float) -> float:
    """Convert parameter value to float with fallback."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return fallback
    return fallback


def _parse_channel_number(channel_id: str) -> int:
    """Parse stream ID to numeric channel number when possible."""
    try:
        return int(channel_id)
    except ValueError:
        return -1


def _to_dtype_code(value: object) -> int:
    """Normalize virtual dtype into nxslib channel type code."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        key = value.strip().upper()
        if key == "INT":
            key = "INT32"
        if hasattr(EDeviceChannelType, key):
            return int(getattr(EDeviceChannelType, key).value)
    return int(EDeviceChannelType.FLOAT.value)
