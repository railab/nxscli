"""Helpers for integrating virtual runtime into nxscli."""

from typing import TYPE_CHECKING

from nxscli.virtual.runtime import VirtualStreamRuntime

if TYPE_CHECKING:
    from nxscli.istream import IServiceRegistry

SERVICE_KEY = "nxscli.virtual"


def get_runtime(registry: "IServiceRegistry") -> VirtualStreamRuntime:
    """Get or create shared virtual runtime service."""
    runtime = registry.service_get(SERVICE_KEY)
    if runtime is not None:
        assert isinstance(runtime, VirtualStreamRuntime)
        return runtime

    runtime = VirtualStreamRuntime()
    registry.service_set(SERVICE_KEY, runtime)
    registry.stream_provider_add(runtime)
    return runtime
