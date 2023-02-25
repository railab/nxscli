"""Module containing Nxscli plugin interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nxscli.phandler import PluginHandler

###############################################################################
# Enum: EPluginType
###############################################################################


class EPluginType(Enum):
    """Nxscli plugin types."""

    NONE = 1
    TEXT = 2
    STATIC = 3
    ANIMATION = 4
    FILE = 5


###############################################################################
# Data: DPluginDescription
###############################################################################


@dataclass
class DPluginDescription:
    """Plugin description."""

    name: str
    plugin: type["IPlugin"]


###############################################################################
# Class: IPlugin
###############################################################################


class IPlugin(ABC):
    """The Nxscli plugin common interface."""

    def __init__(self, ptype: EPluginType) -> None:
        """Initialize a Nxslib plugin.

        :param ptype: plugin type
        """
        self._ptype = ptype
        self._handled = False
        self._phandler: "PluginHandler"

    @property
    def ptype(self) -> EPluginType:
        """Get plugin type."""
        return self._ptype

    @property
    def handled(self) -> bool:
        """Get handled flag."""
        return self._handled

    @handled.setter
    def handled(self, val: bool) -> None:
        """Set handled flag.

        :param val: plugin handled state
        """
        self._handled = val

    def wait_for_plugin(self) -> bool:
        """Return True if plugin is dont't need to wait."""
        return True

    @property
    @abstractmethod
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""

    def connect_phandler(self, phandler: "PluginHandler") -> None:
        """Connect phandler.

        :param phandler: plugin handler instance
        """
        self._phandler = phandler

    @abstractmethod
    def stop(self) -> None:
        """Interface method."""

    @abstractmethod
    def start(self, kwargs: Any) -> bool:
        """Interface method.

        :param kwargs: plugin specific arguments
        """

    @abstractmethod
    def data_wait(self, timeout: float = 0.0) -> bool:
        """Return True if data are ready.

        :param timeout: data wait timeout
        """

    @abstractmethod
    def result(self) -> Any:
        """Interface method."""


###############################################################################
# Class: IPluginNone
###############################################################################


class IPluginNone(IPlugin):
    """None-type plugin."""

    def __init__(self) -> None:
        """Initialize none-type plugin."""
        super().__init__(EPluginType.NONE)


###############################################################################
# Class: IPluginText
###############################################################################


class IPluginText(IPlugin):
    """Text-type plugin."""

    def __init__(self) -> None:
        """Initialize text-type plugin."""
        super().__init__(EPluginType.TEXT)


###############################################################################
# Class: IPluginPlotStatic
###############################################################################


class IPluginPlotStatic(IPlugin):
    """Static-plot plugin."""

    def __init__(self) -> None:
        """Initialize static-plot-type plugin."""
        super().__init__(EPluginType.STATIC)


###############################################################################
# Class: IPluginPlotDynamic
###############################################################################


class IPluginPlotDynamic(IPlugin):
    """Dynamic-plot plugin."""

    def __init__(self) -> None:
        """Initialize dynamic-plot-type plugin."""
        super().__init__(EPluginType.ANIMATION)


###############################################################################
# Class: IPluginFile
###############################################################################


class IPluginFile(IPlugin):
    """File-type plugin."""

    def __init__(self) -> None:
        """Initialize file-type plugin."""
        super().__init__(EPluginType.FILE)
