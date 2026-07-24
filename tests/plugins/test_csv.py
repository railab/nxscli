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


def test_plugincsv_handle_blocks_numeric_columns() -> None:
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
    pdata = type("Q", (), {"vdim": 3})()

    block = DNxscopeStreamBlock(
        data=np.array([[0.5966366, 0.119444996, 10.011609]], dtype=np.float32),
        meta=None,
    )
    plugin._handle_blocks([block], pdata, 0)

    value = out.getvalue()
    # values must be exported as plain numbers, not "np.float32(...)"
    assert "np.float32" not in value
    # each value must land in its own column (space-delimited)
    assert value.strip() == "0.5966366 0.119444996 10.011609"


def test_plugincsv_handle_blocks_numeric_columns_with_meta() -> None:
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

    block = DNxscopeStreamBlock(
        data=np.array([[1.0], [2.0]]),
        meta=np.array([[7, 8], [9, 10]]),
    )
    plugin._handle_blocks([block], pdata, 0)

    assert "np.float32" not in out.getvalue()
    # meta values are appended as extra columns
    lines = out.getvalue().strip().splitlines()
    assert lines[0] == "1.0 7 8"
    assert lines[1] == "2.0 9 10"


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
