"""Top level module for Nxscli."""

import importlib.metadata

# version in pyproject.toml
__version__ = importlib.metadata.version(__package__ or __name__)
