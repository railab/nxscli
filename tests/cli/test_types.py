import click
import pytest

from nxscli.cli.types import (
    Channels,
    Samples,
    StringList,
    StringList2,
    Trigger,
    get_list_from_str,
    get_list_from_str2,
)


def test_get_list_from_str():
    assert get_list_from_str("") == []
    assert get_list_from_str("a,b") == ["a", "b"]
    assert get_list_from_str("a+a", char="+") == ["a", "a"]
    assert get_list_from_str("ala,ala,bala") == ["ala", "ala", "bala"]

    assert get_list_from_str2("") == []
    assert get_list_from_str2("a,b,c,d") == [["a", "b", "c", "d"]]
    assert get_list_from_str2("a,b;c,d") == [["a", "b"], ["c", "d"]]


def test_samples():
    s = Samples()

    assert s.convert("1", None, None) == 1
    assert s.convert("i", None, None) == -1

    with pytest.raises(click.BadParameter):
        s.convert("a", None, None)


def test_channels() -> None:
    ch = Channels()

    all_ch = ch.convert("all", None, None)
    assert len(all_ch) == 1 and all_ch[0].is_all

    phy = ch.convert("0,1", None, None)
    assert [x.physical_id() for x in phy] == [0, 1]

    virt = ch.convert("v0,v12", None, None)
    assert [x.virtual_name() for x in virt] == ["v0", "v12"]

    with pytest.raises(click.BadParameter):
        ch.convert("256", None, None)

    with pytest.raises(AssertionError):
        ch.convert("vA", None, None)


def test_trigger():
    t = Trigger()

    assert t.convert("g:on", None, None)
    assert t.convert("0:on", None, None)
    assert t.convert("0:on;1:off", None, None)
    assert t.convert("0:off;1:er#0,1,2", None, None)
    assert t.convert("0:off;1:er@0,1,2", None, None)
    assert t.convert("0:off;1:er@0#1,1,2", None, None)
    assert t.convert("0:off;1:er#1@1,1,2", None, None)

    parsed = t.convert(
        "g:er#17,0,0.5,mode=stop_after,post=64,holdoff=8,rearm=true",
        None,
        None,
    )
    req = parsed[-1]
    assert req.srcchan == 17
    assert req.mode == "stop_after"
    assert req.post_samples == 64
    assert req.holdoff == 8
    assert req.rearm is True

    parsed = t.convert("1:er@1,0,0.5,pre=32", None, None)
    req = parsed[1]
    assert req.vect == 1
    assert req.pre_samples == 32

    parsed = t.convert("1:we,0,-0.25,0.25", None, None)
    assert parsed[1].ttype == "we"
    assert parsed[1].params == ["0", "-0.25", "0.25"]

    parsed = t.convert("1:wx#v0,0,-0.5,0.5", None, None)
    assert parsed[1].ttype == "wx"
    assert parsed[1].srcchan is not None
    assert parsed[1].srcchan.virtual_name() == "v0"

    parsed = t.convert("1:er#v0,0,0.5", None, None)
    assert parsed[1].srcchan is not None
    assert parsed[1].srcchan.virtual_name() == "v0"

    parsed = t.convert("1:er,0,0.5,rearm=false", None, None)
    assert parsed[1].rearm is False

    with pytest.raises(click.BadParameter):
        t.convert("1:er,0,0.5,rearm=maybe", None, None)

    with pytest.raises(click.BadParameter):
        t.convert("1:er,0,0.5,unknown=1", None, None)

    with pytest.raises(click.BadParameter):
        t.convert("1:er#vbad,0,0.5", None, None)


def test_stringlist():
    s = StringList()

    assert s.convert("1,2,3", None, None) == ["1", "2", "3"]


def test_stringlist2():
    s = StringList2()

    assert s.convert("1,2,3;4,5,6", None, None) == [
        ["1", "2", "3"],
        ["4", "5", "6"],
    ]
