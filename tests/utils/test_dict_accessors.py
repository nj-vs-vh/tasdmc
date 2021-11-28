import pytest
from pytest import param

from tasdmc.utils import get_dot_notation, items_dot_notation


@pytest.mark.parametrize(
    "input_dict, dot_notated_key, expected_value",
    [
        param({"hello": "world"}, "hello", "world"),
        param({"one": 1, "two": 2}, "one", 1),
        param({"nested": {"one": 1, "two": 2}, "two": 2}, "nested.one", 1),
        param({"nested": {"one": 1, "two": {"foo": None, "bar": 10000}}, "two": 2}, "nested.two.foo", None),
    ]
)
def test_get_dot_notation(input_dict, dot_notated_key, expected_value):
    assert get_dot_notation(input_dict, dot_notated_key) == expected_value


def test_get_dot_notation_with_default():
    d = {"nothing": "here"}
    key = "something"
    assert get_dot_notation(d, key, default=1) == 1
    assert get_dot_notation(d, key, default=None) == None
    with pytest.raises(KeyError):
        get_dot_notation(d, key)


def test_items_dot_notation():
    d = {
          "nested":
            {
                "dict": {"one": 1, "two": 2},
                "list": [4, 5, 6]
            },
        "top": "level"
    }

    expected = [
        ("nested.dict.one", 1),
        ("nested.dict.two", 2),
        ("nested.list", [4, 5, 6]),  # no recursion into lists!
        ("top", "level"),
    ]
    assert list(items_dot_notation(d)) == expected
