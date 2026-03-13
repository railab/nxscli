"""Typed channel reference model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelRef:
    """Channel reference for physical/virtual/all channel selectors."""

    kind: str
    value: int | None = None

    @classmethod
    def all_channels(cls) -> "ChannelRef":
        """Select all physical channels."""
        return cls(kind="all", value=None)

    @classmethod
    def physical(cls, channel_id: int) -> "ChannelRef":
        """Select physical channel ``channel_id``."""
        return cls(kind="physical", value=channel_id)

    @classmethod
    def virtual(cls, virtual_id: int) -> "ChannelRef":
        """Select virtual channel ``v{virtual_id}``."""
        return cls(kind="virtual", value=virtual_id)

    @property
    def is_all(self) -> bool:
        """Return ``True`` if this is all-physical selector."""
        return self.kind == "all"

    @property
    def is_physical(self) -> bool:
        """Return ``True`` if this is physical channel selector."""
        return self.kind == "physical"

    @property
    def is_virtual(self) -> bool:
        """Return ``True`` if this is virtual channel selector."""
        return self.kind == "virtual"

    def physical_id(self) -> int:
        """Return physical channel id."""
        if not self.is_physical:
            raise ValueError("not a physical channel reference")
        assert self.value is not None
        return self.value

    def virtual_name(self) -> str:
        """Return virtual channel name (for example ``v0``)."""
        if not self.is_virtual:
            raise ValueError("not a virtual channel reference")
        assert self.value is not None
        return f"v{self.value}"
