"""Module containt the nxscli handler implementation."""

from typing import TYPE_CHECKING, Any, Sequence

from nxscli.channelref import ChannelRef
from nxscli.idata import PluginDataCb
from nxscli.logger import logger
from nxscli.stream_hub import SharedStreamProvider
from nxscli.trigger import DTriggerConfigReq, TriggerHandler, trigger_from_req

if TYPE_CHECKING:
    import queue

    from nxslib.dev import Device, DeviceChannel
    from nxslib.nxscope import NxscopeHandler

    from nxscli.iplugin import DPluginDescription, IPlugin
    from nxscli.istream import IStreamProvider


###############################################################################
# Class: PluginHandler
###############################################################################


class PluginHandler:
    """A class implementing a plugins handler."""

    def __init__(self, plugins: list["DPluginDescription"] | None = None):
        """Initialize a plugin handler.

        :param plugins: a list with plugins
        """
        self._nxs: "NxscopeHandler" | None = None  # noqa: TC010
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
        self._providers: list["IStreamProvider"] = [SharedStreamProvider()]
        self._services: dict[str, Any] = {}

    def __del__(self) -> None:
        """Raise assertion if not cleaned."""
        if not self._cleanup_done:
            raise AssertionError("PluginHandler not cleaned")

    def __enter__(self) -> "PluginHandler":
        """Return self on context manager entry."""
        return self

    def __exit__(self, *_: object) -> None:
        """Clean up on context manager exit."""
        self.cleanup()

    def _chanlist_gen(
        self, channels: Sequence[ChannelRef] | None
    ) -> list["DeviceChannel"]:
        assert self.dev
        refs = self._channel_refs(channels, default_all=False)
        # convert special keys for all channels
        # get channels data
        ret: list["DeviceChannel"] = []
        for ref in refs:
            if ref.is_all:  # pragma: no cover
                for chid in range(self.dev.data.chmax):
                    channel = self.channel_get(ChannelRef.physical(chid))
                    if channel is None:
                        raise AssertionError
                    ret.append(channel)
                continue

            channel = self.channel_get(ref)
            if channel is None:
                raise AssertionError
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

            if channel.data.chan < 0:
                continue

            if self._nxs.dev_channel_get(channel.data.chan) is None:
                continue

            # enable channel
            self._nxs.ch_enable(channel.data.chan)

    def _chanlist_div(self, div: int | list[int]) -> None:
        assert self._nxs
        if isinstance(div, int):
            for channel in self._chanlist:
                if channel.data.chan < 0:
                    continue
                if self._nxs.dev_channel_get(channel.data.chan) is not None:
                    self._nxs.ch_divider(channel.data.chan, div)
        else:
            # divider list configuration must cover all configured channels
            assert len(div) == len(self._chanlist)
            for i, channel in enumerate(self._chanlist):
                if channel.data.chan < 0:
                    continue
                if self._nxs.dev_channel_get(channel.data.chan) is not None:
                    self._nxs.ch_divider(channel.data.chan, div[i])

    def _provider_channels(self) -> list["DeviceChannel"]:
        channels: list["DeviceChannel"] = []
        for provider in self._providers:
            channels.extend(provider.channel_list())
        return channels

    def _channel_ref(self, value: Any) -> ChannelRef:
        if isinstance(value, ChannelRef):
            return value
        if isinstance(value, int):
            if value == -1:
                return ChannelRef.all_channels()
            return ChannelRef.physical(value)
        token = value.strip()
        if token.startswith("v"):
            vnum = token[1:]
            if not vnum.isnumeric():
                raise ValueError(f"Invalid virtual channel: {value}")
            return ChannelRef.virtual(int(vnum))
        if token.isnumeric():
            return ChannelRef.physical(int(token))
        raise ValueError(f"Invalid channel token: {value}")

    def _channel_refs(
        self,
        channels: Sequence[ChannelRef] | None,
        default_all: bool,
    ) -> list[ChannelRef]:
        if channels is None:
            if default_all:
                return [ChannelRef.all_channels()]
            return []
        return [self._channel_ref(x) for x in channels]

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

    @property
    def nxscope(self) -> "NxscopeHandler":
        """Get NxScope handler.

        :return: NxscopeHandler instance
        :raises AssertionError: If nxscope is not connected
        """
        assert self._nxs
        return self._nxs

    def get_enabled_channels(self, applied: bool = True) -> tuple[int, ...]:
        """Get enabled channels from NxScope."""
        return self.nxscope.get_enabled_channels(applied=applied)

    def get_channel_divider(self, chid: int, applied: bool = True) -> int:
        """Get channel divider from NxScope."""
        return self.nxscope.get_channel_divider(chid, applied=applied)

    def get_channel_dividers(self, applied: bool = True) -> tuple[int, ...]:
        """Get channel dividers from NxScope."""
        return self.nxscope.get_channel_dividers(applied=applied)

    def get_channels_state(self, applied: bool = True) -> Any:
        """Get channels state snapshot from NxScope."""
        return self.nxscope.get_channels_state(applied=applied)

    def get_device_capabilities(self) -> Any:
        """Get device capabilities snapshot from NxScope."""
        return self.nxscope.get_device_capabilities()

    def get_stream_stats(self) -> Any:
        """Get stream stats snapshot from NxScope."""
        return self.nxscope.get_stream_stats()

    def collect_inputhooks(self) -> list[Any]:
        """Collect inputhooks from all loaded plugins.

        :return: list of inputhook functions from plugins that provide them
        """
        hooks = []
        for plugin_cls in self._plugins.values():
            hook = plugin_cls.get_inputhook()
            if hook is not None:
                hooks.append(hook)
        return hooks

    def plugin_start_dynamic(self, name: str, **kwargs: Any) -> int:
        """Start a plugin dynamically at runtime.

        :param name: Plugin name
        :param kwargs: Plugin-specific configuration

        :return: Plugin ID for later reference
        """
        from nxscli.iplugin import EPluginType

        # Get plugin class
        cls = self._plugins[name]

        # Create plugin instance
        plugin = cls()  # type: ignore

        # Connect to plugin handler
        plugin.connect_phandler(self)

        # Start the plugin
        if not plugin.start(kwargs):  # pragma: no cover
            logger.error("failed to start plugin %s", str(plugin))
            return -1

        # For plot plugins (STATIC/ANIMATION), call result() to show the plot
        # This is equivalent to what handle_plugin() does in the normal flow
        if plugin.ptype in (EPluginType.STATIC, EPluginType.ANIMATION):
            plugin.result()

        # Add to started list
        self._started.append((plugin, kwargs))
        pid = len(self._started) - 1

        logger.info("dynamically started %s with pid=%d", str(plugin), pid)
        return pid

    def plugin_stop_dynamic(self, pid: int) -> None:
        """Stop a running plugin by ID.

        :param pid: Plugin ID from plugin_start_dynamic()

        :raises IndexError: If plugin ID is invalid
        """
        if pid < 0 or pid >= len(self._started):
            raise IndexError(f"Invalid plugin ID: {pid}")

        plugin, _ = self._started[pid]
        plugin.stop()
        logger.info("stopped plugin with pid=%d", pid)

        # Remove from started list
        self._started.pop(pid)

    def get_started_plugins(self) -> tuple[tuple[int, str], ...]:
        """Get list of started plugins.

        :return: Tuple of (pid, plugin_name) pairs where plugin_name
            is the registered name (not class name)
        """
        result = []
        for i, (plugin, _) in enumerate(self._started):
            # Find registered name for this plugin class
            plugin_class = type(plugin)
            name = None
            for reg_name, reg_class in self._plugins.items():
                if reg_class == plugin_class:
                    name = reg_name
                    break
            if name is None:
                # Fallback to class name if not found
                name = plugin_class.__name__
            result.append((i, name))
        return tuple(result)

    def cleanup(self) -> None:
        """Clean up - must be called after instance use."""
        # disconnect nxscope if connected
        self.nxscope_disconnect()
        # clean up triggers
        TriggerHandler.cls_cleanup()
        self._cleanup_done = True

    def cb_get(self) -> PluginDataCb:
        """Get callbacks for plugins."""
        return PluginDataCb(self.stream_sub, self.stream_unsub)

    def service_set(self, name: str, service: Any) -> None:
        """Register named service for extensions."""
        self._services[name] = service

    def service_get(self, name: str) -> Any:
        """Get named service for extensions."""
        return self._services.get(name)

    def stream_provider_add(self, provider: "IStreamProvider") -> None:
        """Register stream provider."""
        self._providers.append(provider)
        if self._nxs is not None:
            provider.on_connect(self._nxs)

    def channel_get(self, channel: ChannelRef) -> "DeviceChannel | None":
        """Get channel from device or registered providers."""
        if self._nxs is not None and channel.is_physical:
            ch = self._nxs.dev_channel_get(channel.physical_id())
            if ch is not None:
                return ch
        for provider in self._providers:
            ch = provider.channel_get(channel)
            if ch is not None:
                return ch
        return None

    def stream_sub(self, channel: ChannelRef) -> "queue.Queue[Any]":
        """Subscribe queue for device/provider channel."""
        assert self._nxs
        for provider in self._providers:
            subq = provider.stream_sub(channel)
            if subq is not None:
                return subq
        if not channel.is_physical:
            raise ValueError(f"Unknown channel: {channel}")
        return self._nxs.stream_sub(channel.physical_id())

    def stream_unsub(self, subq: "queue.Queue[Any]") -> None:
        """Unsubscribe queue from device/provider channel."""
        for provider in self._providers:
            if provider.stream_unsub(subq):
                return
        if self._nxs is not None:
            self._nxs.stream_unsub(subq)

    def stream_start(self) -> None:
        """Start stream."""
        assert self._nxs
        self._nxs.stream_start()
        for provider in self._providers:
            provider.on_stream_start()

    def stream_stop(self) -> None:
        """Stop stream."""
        for provider in self._providers:
            provider.on_stream_stop()
        assert self._nxs
        self._nxs.stream_stop()

    def nxscope_disconnect(self) -> None:
        """Disconnect from NxScope device."""
        if self._nxs:
            logger.info("disconnecting from nxs device...")
            for provider in self._providers:
                provider.on_disconnect()
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
        for provider in self._providers:
            provider.on_connect(self._nxs)
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

    def chanlist_plugin(  # noqa: C901
        self, channels: Sequence[ChannelRef] | None
    ) -> list["DeviceChannel"]:
        """Prepare channels list for a plugin.

        :param chanlist: a list with plugin channels
        """
        assert self.dev

        refs = self._channel_refs(channels, default_all=True)
        chanlist = []

        # If no channels configured in phandler (dynamic mode),
        # get them directly from device
        if not self._chanlist:
            if refs and refs[0].is_all:
                # All channels
                for chid in range(self.dev.data.chmax):
                    ch = self.channel_get(ChannelRef.physical(chid))
                    if ch and ch.data.is_valid:
                        chanlist.append(ch)
                for ch in self._provider_channels():
                    if ch.data.is_valid:
                        chanlist.append(ch)
            else:
                # Specific channels
                for ref in refs:
                    ch = self.channel_get(ref)
                    if ch and ch.data.is_valid:
                        chanlist.append(ch)
        else:
            # Normal mode: filter from configured chanlist
            if refs and not refs[0].is_all:
                # plugin specific channels configuration
                for chan in self.chanlist:  # pragma: no cover
                    if any(
                        ref.is_physical and ref.value == chan.data.chan
                        for ref in refs
                    ):
                        chanlist.append(chan)
                    else:  # pragma: no cover
                        pass
                for ref in refs:
                    if ref.is_virtual:
                        ch = self.channel_get(ref)
                        if ch and ch.data.is_valid and ch not in chanlist:
                            chanlist.append(ch)
            else:
                chanlist = self.chanlist

        return chanlist

    def channels_configure(
        self,
        channels: Sequence[ChannelRef] | None,
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

        logger.info(
            "configure channels = %s divider = %s", str(channels), str(div)
        )

        refs = self._channel_refs(channels, default_all=False)
        physical_channels = [x for x in refs if x.is_physical]
        self._chanlist = self._chanlist_gen(physical_channels)
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
