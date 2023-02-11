"""Module containt the nxscli handler implementation."""

from typing import TYPE_CHECKING, Any

from nxslib.nxscope import NxscopeHandler

from nxscli.idata import PluginData, PluginDataCb
from nxscli.iplugin import IPlugin
from nxscli.logger import logger
from nxscli.plot_mpl import PluginPlotMpl
from nxscli.trigger import TriggerHandler, trigger_from_str

if TYPE_CHECKING:
    from nxslib.dev import Device, DeviceChannel


###############################################################################
# Class: PluginHandler
###############################################################################


class PluginHandler:
    """A class implementing a plugins handler."""

    def __init__(self, plugins: list | None = None):
        """Initialize a plugin handler.

        :param plugins: a list with plugins
        """
        self._nxs: NxscopeHandler | None = None
        self._plugins = {}

        if plugins:
            for cls in plugins:
                self._validate_plugin(cls)
                self._plugins[cls[0]] = cls[1]

        self._enabled: list = []
        self._started: list = []
        self._triggers: dict = {}

        # stream flags
        self._stream = False

    def __del__(self) -> None:
        """Disconnect nxscope if connected."""
        self.nxscope_disconnect()

    def _validate_plugin(self, cls: tuple) -> None:
        assert isinstance(cls, tuple)
        assert isinstance(cls[0], str)
        assert callable(cls[1])

    @property
    def names(self) -> list[str]:
        """Get plugins names."""
        return list(self._plugins.keys())

    @property
    def plugins(self) -> dict[str, IPlugin]:
        """Get loaded plugins."""
        return self._plugins

    @property
    def chanlist(self) -> list["DeviceChannel"]:
        """Get configured channels."""
        assert self._nxs
        return self._nxs.chanlist

    @property
    def dev(self) -> "Device | None":
        """Get Nxscope device info."""
        assert self._nxs
        return self._nxs.dev

    @property
    def stream(self) -> bool:
        """Get stream flag."""
        return self._stream

    @property
    def enabled(self) -> list:
        """Get enabled plugins."""
        return self._enabled

    def stream_start(self) -> None:
        """Start stream."""
        assert self._nxs
        self._nxs.stream_start()

    def stream_stop(self) -> None:
        """Stop stream."""
        assert self._nxs
        self._nxs.stream_stop()

    def nxscope_disconnect(self) -> None:
        """Disconnect from NxScope device."""
        logger.info("disconnecting from nxs device...")
        if self._nxs:
            # connect nxscope device
            self._nxs.disconnect()
        logger.info("disconnected!")

    def nxscope_connect(self, nxs: NxscopeHandler) -> None:
        """Connect Nxslib instance.

        :param nxs: Nxscope handler
        """
        assert isinstance(nxs, NxscopeHandler)
        self._nxs = nxs
        logger.info("connecting to nxs device...")
        # connect nxscope device
        self._nxs.connect()
        logger.info("connected!")

    def plugin_add(self, cls: tuple) -> None:
        """Add plugin.

        :param cls: tuple with plugin data
        """
        self._validate_plugin(cls)
        self._plugins[cls[0]] = cls[1]

    def plugin_get(self, name: str) -> IPlugin:
        """Get plugin by name.

        :param name: plugin name
        """
        return self._plugins[name]

    def enable(self, name: str, **kwargs: Any) -> int:
        """Enable plugin.

        :param name: plugin name
        :param kwargs: implementation specific arguments
        """
        pid = len(self._enabled)
        plugin = [pid, self._plugins[name], kwargs]
        logger.info("enable %s", str(plugin))
        self._enabled.append(plugin)
        return pid

    def disable(self, pid: int) -> None:
        """Disable plugin with a given ID.

        :param pid: disable plugin by ID
        """
        found = False
        i = 0
        for x in self._enabled:
            if pid == x[0]:
                found = True
                break
            i += 1
        if found:
            logger.info("disable %d %s", pid, str(self._enabled[i]))
            self._enabled.pop(i)
        else:
            raise AttributeError

    def start(self) -> None:
        """Start all enabled plugins."""
        for plg in self._enabled:
            pid, cls, args = plg

            # create instance
            plugin = cls()
            assert isinstance(plugin, IPlugin)

            # we need data stream
            if plugin.stream is True:
                self._stream = True

            plugin.connect_phandler(self)
            if not plugin.start(args):  # pragma: no cover
                logger.error("failed to start plugin %s", str(plugin))
            else:
                self._started.append([plugin, args])
            logger.info("started %s", str(plugin))

        # start stream if needed
        if self.stream:
            self.stream_start()

    def stop(self) -> None:
        """Stop stream and all started plugins."""
        if self._stream is True:
            self.stream_stop()

        for plg, _ in self._started:
            plg.stop()

    def ready(self) -> list:
        """Wait for results from enabled plugins."""
        ret = []
        for plg in self._started:
            plugin, _ = plg
            # blocking
            if plugin.data_wait():
                ret.append(plugin)

        return ret

    def poll(self) -> list | None:
        """Pool for results from enabled plugins."""
        nothandled = 0
        for plg in self._started:
            plugin, _ = plg
            if not plugin.handled:
                nothandled += 1
        if not nothandled:
            return None

        ret = []
        for plg in self._started:
            plugin, _ = plg
            if not plugin.handled:
                if plugin.data_wait(0.1):
                    ret.append(plugin)
                    plugin.handled = True
            else:  # pragma: no cover
                pass

        return ret

    def trigger_get(self, chid: int, src: dict | None = None) -> list:
        """Get trigger for a given channel.

        :param chid: channel ID
        :param src: trigger configuration source
        """
        # get data from plugin private dict or global dict
        if src:
            array = src
        else:
            array = self._triggers

        # get trigger configuration from a given source
        try:
            trg = array[chid]
        except KeyError:
            # check for global configuration key
            globkey = -1
            if globkey in array:
                trg = array[globkey]
            else:
                # default on
                trg = [("on", None)]
        return trg

    def data_handler(
        self, chanlist: list["DeviceChannel"], trig: list[TriggerHandler]
    ) -> PluginData:
        """Prepare data handler.

        :param chanlist: a list with plugin channels
        """
        assert self._nxs
        assert len(chanlist) == len(trig)

        logger.info("prepare data %s", str(chanlist))

        cb = PluginDataCb(self._nxs.stream_sub, self._nxs.stream_unsub)
        return PluginData(chanlist, trig, cb)

    def plot_handler(
        self,
        chanlist: list["DeviceChannel"],
        trig: list[TriggerHandler],
        dpi: float = 100.0,
        fmt: str = "",
    ) -> PluginPlotMpl:
        """Prepare plot handler.

        :param chanlist: a list with plugin channels
        :param dpi: figure DPI
        :param fmt: plot format
        """
        assert self._nxs
        assert len(chanlist) == len(trig)

        logger.info("prepare plot %s", str(chanlist))

        cb = PluginDataCb(self._nxs.stream_sub, self._nxs.stream_unsub)
        return PluginPlotMpl(chanlist, trig, cb, dpi, fmt)

    def chanlist_plugin(self, channels: list[int]) -> list["DeviceChannel"]:
        """Prepare channels list for a plugin.

        :param chanlist: a list with plugin channels
        """
        chanlist = []
        if channels and channels[0] != -1:
            # plugin specific channels configuration
            for chan in self.chanlist:
                if chan.chan in channels:
                    chanlist.append(chan)
                else:  # pragma: no cover
                    pass
        else:
            chanlist = self.chanlist

        return chanlist

    def channels_configure(
        self, channels: list[int], div: int | list[int] = 0
    ) -> None:
        """Configure channels.

        :param chanlist: a list with plugin channels
        :param div: divider configuration
        """
        assert self._nxs
        self._nxs.channels_configure(channels, div)

    def triggers_configure(self, triggers: dict) -> None:
        """Configure triggers.

        :param triggers: dict with triggers configuration
        """
        self._triggers = triggers

    def triggers_plugin(
        self, chanlist: list["DeviceChannel"], triggers: dict | None
    ) -> list[TriggerHandler]:
        """Prepare triggers list for a plugin.

        :param chanlist: a list with plugin channels
        :param triggers: a list with plugin triggers
        """
        trgs = []
        if triggers:
            # plugin specific triggers
            for chan in chanlist:
                tcfg = self.trigger_get(chan.chan, triggers)
                trgs.append(tcfg)
        else:
            # global configured triggers
            for chan in chanlist:
                tcfg = self.trigger_get(chan.chan)
                trgs.append(tcfg)

        ret = []
        for tcfg in trgs:
            # get trigger configuration
            dtc = trigger_from_str(tcfg)
            # get trigger
            trig = TriggerHandler(dtc)
            ret.append(trig)
        return ret
