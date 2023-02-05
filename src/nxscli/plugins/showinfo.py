"""Module containing showinfo plugin."""

from nxscli.iplugin import IPluginText

###############################################################################
# Class: PluginShowinfo
###############################################################################


class PluginShowinfo(IPluginText):
    """Plugin that shows device information."""

    def __init__(self):
        """Initialize showinfo plugin."""
        super().__init__()
        self._return = None

    @property
    def stream(self) -> bool:
        """Return True if this plugin needs stream."""
        return False

    def stop(self):
        """Stop showinfo plugin."""

    def data_wait(self, timeout=None):
        """Return True if data are ready."""
        return True

    def start(self, _) -> bool:
        """Start showinfo plugin."""
        assert self._phandler
        assert self._phandler.dev

        dev = self._phandler.dev

        ret = {}
        ret["cmn"] = {}
        ret["cmn"]["chmax"] = dev.chmax
        ret["cmn"]["flags"] = dev.flags
        ret["cmn"]["rxpadding"] = dev.rxpadding

        tmp = []
        for chid in range(dev.chmax):
            chinfo = dev.channel_get(chid)
            assert chinfo
            chan = {}
            chan["chan"] = chinfo.chan
            chan["type"] = chinfo._type
            chan["vdim"] = chinfo.vdim
            chan["name"] = chinfo.name

            tmp.append(chinfo)

        ret["channels"] = tmp  # type: ignore

        self._return = ret

        return True

    def result(self):
        """Get showinfo plugin result."""
        return self._return
