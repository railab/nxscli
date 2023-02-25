import click
import pytest

from nxscli.cli.types import (
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


def test_trigger():
    t = Trigger()

    assert t.convert("g:on", None, None)
    assert t.convert("0:on", None, None)
    assert t.convert("0:on;1:off", None, None)
    assert t.convert("0:off;1:er#0,1,2", None, None)
    assert t.convert("0:off;1:er@0,1,2", None, None)
    assert t.convert("0:off;1:er@0#1,1,2", None, None)
    assert t.convert("0:off;1:er#1@1,1,2", None, None)


def test_stringlist():
    s = StringList()

    assert s.convert("1,2,3", None, None) == ["1", "2", "3"]


def test_stringlist2():
    s = StringList2()

    assert s.convert("1,2,3;4,5,6", None, None) == [
        ["1", "2", "3"],
        ["4", "5", "6"],
    ]
