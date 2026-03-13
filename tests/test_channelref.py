import pytest

from nxscli.channelref import ChannelRef


def test_channelref_accessors() -> None:
    p = ChannelRef.physical(3)
    v = ChannelRef.virtual(5)

    assert p.physical_id() == 3
    assert v.virtual_name() == "v5"

    with pytest.raises(ValueError):
        ChannelRef.all_channels().physical_id()

    with pytest.raises(ValueError):
        ChannelRef.all_channels().virtual_name()
