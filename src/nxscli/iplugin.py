"""Module containing Nxscli plugin interfaces."""

from abc import ABC, abstractmethod
from enum import Enum

###############################################################################
# Enum: EPluginType
###############################################################################


class EPluginType(Enum):
    """Nxscli plugin types."""

    TEXT = 1
    PLOT = 2
    ANIMATION = 3
    FILE = 4


###############################################################################
# Class: IPlugin
###############################################################################


class IPlugin(ABC):
    """The Nxscli plugin common interface."""

    def __init__(self, ptype: EPluginType):
        """Initialize a Nxslib plugin."""
        if not isinstance(ptype, EPluginType):
            raise TypeError

        self._ptype = ptype
        self._handled = False
        self._phandler = None

    @property
    def ptype(self) -> EPluginType:
        """Get plugin type."""
        return self._ptype

    @property
    def handled(self) -> bool:
        """Get handled flag."""
        return self._handled

    @handled.setter
    def handled(self, val: bool):
        """Set handled flag."""
        self._handled = val

    @property
    @abstractmethod
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""

    def connect_phandler(self, phandler):
        """Connect phandler."""
        self._phandler = phandler

    @abstractmethod
    def stop(self) -> None:
        """Interface method."""

    @abstractmethod
    def start(self, kwargs) -> bool:
        """Interface method."""

    @abstractmethod
    def data_wait(self, timeout=None) -> bool:
        """Return True if data are ready."""

    @abstractmethod
    def result(self):
        """Interface method."""


###############################################################################
# Class: IPluginText
###############################################################################


class IPluginText(IPlugin):
    """Text-type plugin."""

    def __init__(self):
        """Initialize text-type plugin."""
        super().__init__(EPluginType.TEXT)


###############################################################################
# Class: IPluginPlotStatic
###############################################################################


class IPluginPlotStatic(IPlugin):
    """Static-plot plugin."""

    def __init__(self):
        """Initialize static-plot-type plugin."""
        super().__init__(EPluginType.PLOT)


###############################################################################
# Class: IPluginPlotDynamic
###############################################################################


class IPluginPlotDynamic(IPlugin):
    """Dynamic-plot plugin."""

    def __init__(self):
        """Initialize dynamic-plot-type plugin."""
        super().__init__(EPluginType.ANIMATION)


###############################################################################
# Class: IPluginPlotFile
###############################################################################


class IPluginPlotFile(IPlugin):
    """File-type plugin."""

    def __init__(self):
        """Initialize file-type plugin."""
        super().__init__(EPluginType.FILE)
