"""Interfaces for additional stream providers."""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import queue

    from nxslib.dev import DeviceChannel
    from nxslib.nxscope import DNxscopeStream, NxscopeHandler

    from nxscli.channelref import ChannelRef


###############################################################################
# Class: IStreamProvider
###############################################################################


class IStreamProvider(Protocol):
    """Provider that can expose additional channels and stream queues."""

    def on_connect(self, nxscope: "NxscopeHandler") -> None:
        """Attach to an active ``NxscopeHandler``."""

    def on_disconnect(self) -> None:
        """Detach from ``NxscopeHandler``."""

    def on_stream_start(self) -> None:
        """React to stream start."""

    def on_stream_stop(self) -> None:
        """React to stream stop."""

    def channel_get(self, channel: "ChannelRef") -> "DeviceChannel | None":
        """Return channel metadata managed by this provider."""

    def channel_list(self) -> tuple["DeviceChannel", ...]:
        """Return all channels managed by this provider."""

    def stream_sub(
        self, channel: "ChannelRef"
    ) -> "queue.Queue[list[DNxscopeStream]] | None":
        """Subscribe to a provider-managed channel queue."""

    def stream_unsub(self, subq: "queue.Queue[list[DNxscopeStream]]") -> bool:
        """Unsubscribe queue. Return ``True`` if queue belonged here."""


###############################################################################
# Class: IServiceRegistry
###############################################################################


class IServiceRegistry(Protocol):
    """Minimal service registry exposed by ``PluginHandler``."""

    def service_get(self, name: str) -> Any:
        """Get registered service."""

    def service_set(self, name: str, service: Any) -> None:
        """Set registered service."""

    def stream_provider_add(self, provider: IStreamProvider) -> None:
        """Add stream provider."""
