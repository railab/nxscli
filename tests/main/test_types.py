from nxscli.main.types import get_list_from_str, get_list_from_str2


def test_get_list_from_str():
    assert get_list_from_str("") == []
    assert get_list_from_str("a,b") == ["a", "b"]
    assert get_list_from_str("a+a", char="+") == ["a", "a"]
    assert get_list_from_str("ala,ala,bala") == ["ala", "ala", "bala"]

    assert get_list_from_str2("") == []
    assert get_list_from_str2("a,b,c,d") == [["a", "b", "c", "d"]]
    assert get_list_from_str2("a,b;c,d") == [["a", "b"], ["c", "d"]]
