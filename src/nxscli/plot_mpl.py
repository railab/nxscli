"""The matplotlib plot specific module."""

import queue
import time
from functools import partial

import matplotlib.pyplot as plt  # type: ignore
from matplotlib import _pylab_helpers  # type: ignore
from matplotlib.animation import FuncAnimation  # type: ignore
from matplotlib.animation import FFMpegWriter, PillowWriter  # type: ignore
from matplotlib.axes import Axes  # type: ignore
from matplotlib.figure import Figure  # type: ignore
from nxslib.dev import DeviceChannel

from nxscli.idata import PluginData, PluginDataCb, PluginQueueData
from nxscli.logger import logger

###############################################################################
# Class: MplManager
###############################################################################


class MplManager:
    """Matplotlib global manager."""

    @staticmethod
    def draw() -> None:  # pragma: no cover
        """Draw an animation."""
        plt.draw()

    @staticmethod
    def fig_is_open() -> list:
        """Return a list of opened figures."""
        return plt.get_fignums()

    @staticmethod
    def pause(interval):  # pragma: no cover
        """Handle Matplotlib events.

        Modified pyplot.pause() without show(False) in the middle.
        """
        manager = _pylab_helpers.Gcf.get_active()
        if manager is not None:
            canvas = manager.canvas
            if canvas.figure.stale:
                canvas.draw_idle()
            # show(block=False)
            canvas.start_event_loop(interval)
        else:
            time.sleep(interval)

    @staticmethod
    def show(block: bool = True) -> None:
        """Show an animation."""
        plt.show(block=block)

    @staticmethod
    def mpl_config():
        """Configure matplotlib."""
        plt.style.use(["ggplot", "fast"])

    @staticmethod
    def figure(dpi: float = 100.0):
        """Get figure."""
        return plt.figure(dpi=dpi)

    @staticmethod
    def close(fig):
        """Close figure."""
        return plt.close(fig)


###############################################################################
# Class: PlotDataCommon
###############################################################################


class PlotDataCommon:
    """A class implementing common plot data."""

    def __init__(self, channel: DeviceChannel):
        """Initialize common plot data."""
        assert isinstance(channel, DeviceChannel)

        self._xdata: list = []
        self._ydata: list = []
        self._vdim = channel.vdim
        self._chan = channel.chan
        for _ in range(self._vdim):
            self._xdata.append([])
            self._ydata.append([])

        self._samples_max = 0

    @property
    def chan(self) -> int:
        """Get channel id."""
        return self._chan

    @property
    def xdata(self) -> list[list]:
        """Get X data."""
        return self._xdata

    @property
    def ydata(self) -> list[list]:
        """Get Y data."""
        return self._ydata

    @property
    def samples_max(self) -> int:
        """Get max samples."""
        return self._samples_max

    @samples_max.setter
    def samples_max(self, smax: int) -> None:
        """Set max samples."""
        self._samples_max = smax

    def xdata_extend(self, data: list[list]) -> None:
        """Extend X data."""
        for i, xdata in enumerate(self._xdata):
            xdata.extend(data[i])

    def ydata_extend(self, data: list[list]) -> None:
        """Extend Y data."""
        for i, ydata in enumerate(self._ydata):
            ydata.extend(data[i])

    def xdata_extend_max(self, data: list[list]) -> None:
        """Extend X data and saturate to a configured number of samples."""
        for i, _ in enumerate(self._xdata):
            self._xdata[i].extend(data[i])
            remove = len(self._xdata[i]) - self._samples_max
            if remove > 0:
                self._xdata[i] = self._xdata[i][remove:]

    def ydata_extend_max(self, data: list[list]) -> None:
        """Extend Y data and saturate to a configured number of samples."""
        for i, _ in enumerate(self._xdata):
            self._ydata[i].extend(data[i])
            remove = len(self._ydata[i]) - self._samples_max
            if remove > 0:
                self._ydata[i] = self._ydata[i][remove:]


###############################################################################
# Class: PlotDataAxesMpl
###############################################################################


class PlotDataAxesMpl(PlotDataCommon):
    """A class implementing common matplotlib axes logic."""

    def __init__(
        self,
        ax: Axes,
        channel: DeviceChannel,
        fmt: str = "",
    ):
        """Initialize matplotlib specific plot data."""
        PlotDataCommon.__init__(self, channel)

        # initialize axis only if numerical channel
        if not channel.is_numerical:
            raise TypeError

        self._ax = ax
        self._fmt = fmt

        # TODO: typing
        self._lns = []
        for _ in range(channel.vdim):
            (line,) = self._ax.plot([], [], fmt)
            self._lns.append(line)

        # set grid
        self.grid_set(True)

        if len(channel.name) > 0:
            self.plot_title = channel.name

    def __str__(self):
        """Format string representation."""
        _str = "PlotDataAxesMpl" + "(channel=" + str(self.chan) + ")"
        return _str

    @property
    def ax(self) -> list[Axes]:
        """Get axes."""
        return self._ax

    # TODO: typing
    @property
    def lns(self):
        """Get lines."""
        return self._lns

    @property
    def xlim(self) -> list:
        """Get pot X limits."""
        return self._ax.get_xlim()

    @property
    def ylim(self) -> list:
        """Get pot Y limits."""
        return self._ax.get_ylim()

    @property
    def plot_title(self) -> str:
        """Get the plot title."""
        return self._ax.get_title()

    @plot_title.setter
    def plot_title(self, title: str) -> None:
        """Set the plot title."""
        self._ax.set_title(title)

    def set_xlim(self, xlim: tuple) -> None:
        """Set plot X limits."""
        self._ax.set_xlim(*xlim)

    def set_ylim(self, ylim: tuple) -> None:
        """Set plot Y limits."""
        self._ax.set_ylim(*ylim)

    def plot(self) -> None:
        """Plot all data."""
        for i in self._ydata:
            self._ax.plot(i, self._fmt)

    def xaxis_disable(self) -> None:
        """Disable x axis ticks."""
        self.xaxis_set_ticks([])

    def xaxis_set_ticks(self, ticks: list) -> None:
        """Set ticks for X axis."""
        self._ax.get_xaxis().set_ticks(ticks)

    def grid_set(self, enable: bool) -> None:
        """Enable grid on plots."""
        self._ax.grid(enable)


###############################################################################
# Class: PluginAnimationCommonMpl
###############################################################################


class PluginAnimationCommonMpl:
    """A class implementing a common matplotlib animation plot logic."""

    def __init__(
        self,
        fig: Figure,
        pdata: PlotDataAxesMpl,
        qdata: PluginQueueData,
        write: str | None,
    ):
        """Initialize animation handler."""
        self._fig = fig
        self._cnt = 0
        self._pdata = pdata
        self._qdata = qdata
        self._ani = None

        if write:  # pragma: no cover
            fps = 10
            logger.info("writer animation to file=%s, fps=%d", write, fps)

            tmp = write.split(".")
            if tmp[-1] == "gif":
                self._writer = PillowWriter(fps=fps)
            elif tmp[-1] == "mp4":
                bitrate = 200
                self._writer = FFMpegWriter(fps=fps, bitrate=bitrate)
            else:
                raise TypeError

            # NOTE: dpi arg set cause overlapping animation
            self._writer.setup(self._fig, write)
        else:
            self._writer = None

    def _animation_init(self, pdata: PlotDataAxesMpl):
        return pdata.lns

    def _animation_frames(self, qdata: PluginQueueData):  # pragma: no cover
        ydata: list[list] = []
        xdata: list[list] = []

        for _ in range(self._qdata.vdim):
            ydata.append([])
            xdata.append([])

        # limit to 100 samples per frame
        for _ in range(100):
            data = []
            try:
                # this must be non-blocking for queue.Empty exception
                data = qdata.queue_get(block=False)
            except queue.Empty:
                break

            # print("qsize=", qdata._queue.qsize())
            for sample in data:
                for i in range(self._qdata.vdim):
                    ydata[i].append(sample[0][i])
                    xdata[i].append(self._cnt)
                self._cnt += 1

        yield xdata, ydata

    def _animation_update(
        self, frame: list, pdata: PlotDataAxesMpl, qdata: PluginQueueData
    ):
        pass  # pragma: no cover

    def pause(self) -> None:
        """Pause an animation."""
        if self._ani is not None:  # pragma: no cover
            self._ani.pause()

    def stop(self) -> None:  # pragma: no cover
        """Stop animation."""
        # TODO: stop animation
        if self._ani:
            if self._ani.event_source:
                self._ani.pause()
        if self._writer:
            self._writer.finish()

    def _animation_update_cmn(self, frame, pdata):  # pragma: no cover
        """Update animation common logic."""
        # no data
        if len(frame[0]) == 0 or len(frame[1]) == 0:
            return pdata.lns

        # implementation specific
        lines = self._animation_update(frame, pdata)

        # handle writer
        if self._writer:
            # self._fig.canvas.flush_events()
            self._writer.grab_frame()

        return lines

    def start(self) -> None:
        """Start an animation."""
        fig = self._fig
        update = partial(self._animation_update_cmn, pdata=self._pdata)
        frames = partial(self._animation_frames, qdata=self._qdata)
        init = partial(self._animation_init, pdata=self._pdata)
        self._ani = FuncAnimation(
            fig,
            update,
            frames,
            init,
            interval=1,
            blit=True,
            cache_frame_data=False,
        )

    def xaxis_disable(self) -> None:  # pragma: no cover
        """Hide x axis."""
        self._pdata.xaxis_disable()

    def yscale_extend(
        self, frame, pdata, scale=1.1
    ) -> None:  # pragma: no cover
        """Extend yscale if needed with a given scale factor."""
        ymin, ymax = pdata.ax.get_ylim()

        new_ymax = ymax
        new_ymin = ymin
        for data in frame:
            # do nothing if empty
            if not data:
                return

            # get min/max
            ytmp = max(data)
            if ytmp > new_ymax:
                new_ymax = ytmp
            ytmp = min(data)
            if ytmp < new_ymin:
                new_ymin = ytmp

        if new_ymax > ymax:
            new_ymax = new_ymax * scale
            ymax = new_ymax  # store for ymin update
            pdata.ax.set_ylim(ymin, new_ymax)
            pdata.ax.figure.canvas.draw()
        if new_ymin < ymin:
            new_ymin = new_ymin * scale
            pdata.ax.set_ylim(new_ymin, ymax)
            pdata.ax.figure.canvas.draw()

    def xscale_extend(
        self, frame, pdata, scale=2.0
    ) -> None:  # pragma: no cover
        """Exten x axis if needed with a agiven scale factor."""
        xmin, xmax = pdata.ax.get_xlim()

        tmax = xmax
        # get min/max
        for i in frame:
            if len(i) > 0:
                tmp = max(i)
                if tmp > tmax:
                    tmax = tmp

        # change x scale
        if tmax > xmax:
            pdata.ax.set_xlim(xmin, scale * xmax)
            pdata.ax.figure.canvas.draw()

    def xscale_saturate(self, _, pdata) -> None:  # pragma: no cover
        """Saturate x axis."""
        xmin, xmax = pdata.ax.get_xlim()

        # change x scale fit for xdata
        new_xmin = pdata.xdata[0]
        new_xmax = pdata.xdata[-1]
        if xmin > new_xmin or xmax < new_xmax:
            pdata.ax.set_xlim(new_xmin, new_xmax)
            # TODO: revisit
            # pdata.ax.figure.canvas.draw()


###############################################################################
# Class: PluginPlotMpl
###############################################################################


class PluginPlotMpl(PluginData):
    """A class implementing matplotlib common plot handler."""

    def __init__(
        self,
        chanlist: list[DeviceChannel],
        cb: PluginDataCb,
        dpi: float = 100.0,
        fmt: str = "",
    ):
        """Intiialize a plot handler."""
        newchanlist = []
        for chan in chanlist:
            # get only numerical channels
            if chan.is_numerical:
                newchanlist.append(chan)
            else:  # pragma: no cover
                logger.info(
                    "NOTE: channel %d not numerical - ignore", chan.chan
                )

        super().__init__(newchanlist, cb)

        self._fig = MplManager.figure(dpi)
        self._ax: list[Axes] = []
        self._ani: list[PluginAnimationCommonMpl] = []
        self._fmt = fmt

        # add subplots
        self._add_subplots(newchanlist)

        self._plist = self._plist_init()

    def __del__(self):
        """Close figure and clean queue handlers."""
        MplManager.close(self._fig)
        super().__del__()

    def _plist_init(self) -> list[PlotDataAxesMpl]:
        ret = []
        for i, channel in enumerate(self._chanlist):
            # initialize plot
            pdata = PlotDataAxesMpl(self._ax[i], channel, fmt=self._fmt)
            # add plot to list
            ret.append(pdata)
        return ret

    def _add_subplots(self, channels: list[DeviceChannel]) -> None:
        """Create subplots from channels list."""
        # remove all current axes
        for ax in self._ax:  # pragma: no cover
            if ax is not None:
                self._fig.delaxes(ax)
                # ax.remove()
            else:
                pass
        self._ax = []

        # show plots only for numerical channels
        chanlist = []
        for chan in channels:
            if chan.is_numerical:
                chanlist.append(chan.chan)
            else:  # pragma: no cover
                pass

        row = len(chanlist)
        col = 1

        i = 1
        for _ in range(len(chanlist)):
            # create subplot for all used numerical channels
            self._ax.append(self._fig.add_subplot(row, col, i))
            i += 1

    @property
    def fig(self):
        """Get figure handler."""
        return self._fig

    @property
    def ani(self) -> list[PluginAnimationCommonMpl]:
        """Return all registered animation isntances."""
        return self._ani

    @property
    def plist(self) -> list[PlotDataAxesMpl]:
        """Get plotdata list."""
        return self._plist

    def ani_append(self, ani: PluginAnimationCommonMpl) -> None:
        """Add animation."""
        self._ani.append(ani)

    def ani_clear(self) -> None:  # pragma: no cover
        """Clear animations."""
        # TODO: fix me, doesnt work
        del self._ani
        self._ani = []

    def plot_clear(self) -> None:
        """Clear plot data."""
        if len(self._ax) > 0:  # pragma: no cover
            for ax in self._ax:
                if ax is not None:
                    ax.cla()
