import csv
import io

import numpy as np
from nxslib.nxscope import DNxscopeStreamBlock

from nxscli.plugins.csv import PluginCsv


def test_plugincsv_init():
    plugin = PluginCsv()

    assert plugin.stream is True

    # TODO:


def test_plugincsv_handle_blocks_none_meta_and_empty_block() -> None:
    plugin = PluginCsv()
    out = io.StringIO()
    writer = csv.writer(
        out,
        delimiter=" ",
        quotechar="|",
        escapechar="\\",
        quoting=csv.QUOTE_MINIMAL,
    )
    plugin._csvwriters = [[writer, out]]
    plugin._samples = 10
    plugin._nostop = False
    plugin._datalen = [0]
    plugin._meta_string = False
    pdata = type("Q", (), {"vdim": 1})()

    block0 = DNxscopeStreamBlock(data=np.empty((0, 1)), meta=None)
    block1 = DNxscopeStreamBlock(data=np.array([[1.0], [2.0]]), meta=None)
    plugin._handle_blocks([block0, block1], pdata, 0)

    assert plugin._datalen == [2]


def test_plugincsv_handle_blocks_meta_string() -> None:
    plugin = PluginCsv()
    out = io.StringIO()
    writer = csv.writer(
        out,
        delimiter=" ",
        quotechar="|",
        escapechar="\\",
        quoting=csv.QUOTE_MINIMAL,
    )
    plugin._csvwriters = [[writer, out]]
    plugin._samples = 10
    plugin._nostop = False
    plugin._datalen = [0]
    plugin._meta_string = True
    pdata = type("Q", (), {"vdim": 1})()

    block = DNxscopeStreamBlock(
        data=np.array([[1.0], [2.0]]),
        meta=np.array([[65], [66]], dtype=np.uint8),
    )
    plugin._handle_blocks([block], pdata, 0)

    assert plugin._datalen == [2]
    assert "A" in out.getvalue()
