"""Module containt the nxscli handler implementation."""

from typing import TYPE_CHECKING, Any

from nxscli.idata import PluginDataCb
from nxscli.logger import logger
from nxscli.trigger import DTriggerConfigReq, TriggerHandler, trigger_from_req

if TYPE_CHECKING:
    from nxslib.dev import Device, DeviceChannel
    from nxslib.nxscope import NxscopeHandler

    from nxscli.iplugin import DPluginDescription, IPlugin


###############################################################################
# Class: PluginHandler
###############################################################################


class PluginHandler:
    """A class implementing a plugins handler."""

    def __init__(self, plugins: list["DPluginDescription"] | None = None):
        """Initialize a plugin handler.

        :param plugins: a list with plugins
        """
        self._nxs: "NxscopeHandler" | None = None
        self._plugins = {}

        if plugins:
            for cls in plugins:
                self._plugins[cls.name] = cls.plugin

        self._enabled: list[tuple[int, type["IPlugin"], Any]] = []
        self._started: list[tuple["IPlugin", Any]] = []
        self._triggers: dict[int, DTriggerConfigReq] = {}

        self._chanlist: list["DeviceChannel"] = []

        # stream flags
        self._stream = False

        self._cleanup_done = False

    def __del__(self) -> None:
        """Raise assertion if not cleaned."""
        if not self._cleanup_done:
            raise AssertionError("PluginHandler not cleaned")

    def _chanlist_gen(self, channels: list[int]) -> list["DeviceChannel"]:
        assert self._nxs
        assert self.dev
        # convert special keys for all channels
        if channels and channels[0] == -1:  # pragma: no cover
            chanlist = list(range(self.dev.data.chmax))
        else:
            assert all(isinstance(x, int) for x in channels)
            chanlist = channels

        # get channels data
        ret = []
        for chan in chanlist:
            channel = self._nxs.dev_channel_get(chan)
            assert channel
            ret.append(channel)

        return ret

    def _chanlist_enable(self) -> None:
        assert self._nxs
        for channel in self._chanlist:
            # ignore not valid channels
            if not channel.data.is_valid:  # pragma: no cover
                logger.info(
                    "NOTE: channel %d not valid - ignore", channel.data.chan
                )
                continue

            # enable channel
            self._nxs.ch_enable(channel.data.chan)

    def _chanlist_div(self, div: int | list[int]) -> None:
        assert self._nxs
        if isinstance(div, int):
            for channel in self._chanlist:
                self._nxs.ch_divider(channel.data.chan, div)
        else:
            # divider list configuration must cover all configured channels
            assert len(div) == len(self._chanlist)
            for i, channel in enumerate(self._chanlist):
                self._nxs.ch_divider(channel.data.chan, div[i])

    @property
    def chanlist(self) -> list["DeviceChannel"]:
        """Get configured channels list."""
        return self._chanlist

    @property
    def names(self) -> list[str]:
        """Get plugins names."""
        return list(self._plugins.keys())

    @property
    def plugins(self) -> dict[str, type["IPlugin"]]:
        """Get loaded plugins."""
        return self._plugins

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
    def enabled(self) -> list[tuple[int, type["IPlugin"], Any]]:
        """Get enabled plugins."""
        return self._enabled

    def cleanup(self) -> None:
        """Clean up - must be called after instance use."""
        # disconnect nxscope if connected
        self.nxscope_disconnect()
        # clean up triggers
        TriggerHandler.cls_cleanup()
        self._cleanup_done = True

    def cb_get(self) -> PluginDataCb:
        """Get callbacks for plugins."""
        assert self._nxs
        return PluginDataCb(self._nxs.stream_sub, self._nxs.stream_unsub)

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
        if self._nxs:
            logger.info("disconnecting from nxs device...")
            # connect nxscope device
            self._nxs.disconnect()
            logger.info("disconnected!")
            self._nxs = None

    def nxscope_connect(self, nxs: "NxscopeHandler") -> None:
        """Connect Nxslib instance.

        :param nxs: Nxscope handler
        """
        self._nxs = nxs
        logger.info("connecting to nxs device...")
        # connect nxscope device
        self._nxs.connect()
        logger.info("connected!")

    def plugin_add(self, cls: tuple[str, type["IPlugin"]]) -> None:
        """Add plugin.

        :param cls: tuple with plugin data
        """
        self._plugins[cls[0]] = cls[1]

    def plugin_get(self, name: str) -> type["IPlugin"]:
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
        plugin = (pid, self._plugins[name], kwargs)
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
            plugin = cls()  # type: ignore

            # we need data stream
            if plugin.stream is True:
                self._stream = True

            plugin.connect_phandler(self)
            if not plugin.start(args):  # pragma: no cover
                logger.error("failed to start plugin %s", str(plugin))
            else:
                self._started.append((plugin, args))
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

    def ready(self) -> list["IPlugin"]:
        """Wait for results from enabled plugins."""
        ret = []
        for plg in self._started:
            plugin, _ = plg
            # blocking
            if plugin.data_wait():
                ret.append(plugin)

        return ret

    def poll(self) -> list["IPlugin"] | None:
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

    def wait_for_plugins(self) -> None:
        """Wait for plugins."""
        while True:
            done = True
            for plg in self._started:
                plugin, _ = plg
                if not plugin.wait_for_plugin():
                    done = False
            # exit from loop if done
            if done:
                break

    def trigger_get(
        self, chid: int, src: dict[int, DTriggerConfigReq] | None = None
    ) -> DTriggerConfigReq:
        """Get trigger for a given channel.

        :param chid: channel ID
        :param src: trigger configuration source
        """
        # get data from plugin private dict or global dict
        if src:
            array = src  # pragma: no cover
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
                trg = DTriggerConfigReq("on", None)
        return trg

    def chanlist_plugin(self, channels: list[int]) -> list["DeviceChannel"]:
        """Prepare channels list for a plugin.

        :param chanlist: a list with plugin channels
        """
        chanlist = []
        if channels and channels[0] != -1:
            # plugin specific channels configuration
            for chan in self.chanlist:  # pragma: no cover
                if chan.data.chan in channels:
                    chanlist.append(chan)
                else:  # pragma: no cover
                    pass
        else:
            chanlist = self.chanlist

        return chanlist

    def channels_configure(
        self,
        channels: list[int],
        div: int | list[int] = 0,
        writenow: bool = False,
    ) -> None:
        """Configure channels.

        The effects of this method are buffered and will
        be applied to the device just before the stream starts
        or can be forced to write with writenow flag.

        :param chans: a list with channels IDs
        :param div: a list with divider values
        :param writenow: write channels configuration now
        """
        assert self._nxs

        logger.info("configure channels = %s divider = %d", str(channels), div)

        self._chanlist = self._chanlist_gen(channels)
        if not self._chanlist:
            return

        # default channels configuration
        self._nxs.channels_default_cfg()

        # enable channels
        self._chanlist_enable()

        # set divider for channels
        self._chanlist_div(div)

        if writenow:
            # write channels configuration
            self._nxs.channels_write()

    def triggers_configure(
        self, triggers: dict[int, DTriggerConfigReq]
    ) -> None:
        """Configure triggers.

        :param triggers: dict with triggers configuration
        """
        self._triggers = triggers

    def triggers_plugin(
        self,
        chanlist: list["DeviceChannel"],
        triggers: dict[int, DTriggerConfigReq] | None,
    ) -> list[TriggerHandler]:
        """Prepare triggers list for a plugin.

        :param chanlist: a list with plugin channels
        :param triggers: a list with plugin triggers
        """
        trgs: list[tuple[int, DTriggerConfigReq]] = []
        if triggers:
            # plugin specific triggers
            for chan in chanlist:  # pragma: no cover
                tcfg = self.trigger_get(chan.data.chan, triggers)
                trgs.append((chan.data.chan, tcfg))
        else:
            # global configured triggers
            for chan in chanlist:
                tcfg = self.trigger_get(chan.data.chan)
                trgs.append((chan.data.chan, tcfg))

        ret = []
        for item in trgs:
            # get trigger configuration
            dtc = trigger_from_req(item[1])
            # get trigger
            trig = TriggerHandler(item[0], dtc)
            ret.append(trig)

        return ret
