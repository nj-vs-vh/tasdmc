import pytest
from pytest import param

from tasdmc.utils import get_dot_notation, set_dot_notation, items_dot_notation


@pytest.mark.parametrize(
    "input_dict, dot_notated_key, expected_value",
    [
        param({"hello": "world"}, "hello", "world"),
        param({"one": 1, "two": 2}, "one", 1),
        param({"nested": {"one": 1, "two": 2}, "two": 2}, "nested.one", 1),
        param({"nested": {"one": 1, "two": {"foo": None, "bar": 10000}}, "two": 2}, "nested.two.foo", None),
    ],
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
    d = {"nested": {"dict": {"one": 1, "two": 2}, "list": [4, 5, 6]}, "top": "level"}

    expected = [
        ("nested.dict.one", 1),
        ("nested.dict.two", 2),
        ("nested.list", [4, 5, 6]),  # no recursion into lists!
        ("top", "level"),
    ]
    assert list(items_dot_notation(d)) == expected


@pytest.mark.parametrize(
    "original, set_key, set_value, expected_modified",
    [
        param({}, "hello", "world", {"hello": "world"}),
        param({"hello": "foo"}, "hello", "bar", {"hello": "bar"}),
        param(
            {"hello": "world", "very": {"nested": {"key": 1}}},
            "very.nested.key",
            2,
            {"hello": "world", "very": {"nested": {"key": 2}}},
        ),
        param(
            {"hello": "world"},
            "very.much.nested.key",
            2,
            {"hello": "world", "very": {"much": {"nested": {"key": 2}}}},
        ),
    ],
)
def test_set_dot_notation(original, set_key, set_value, expected_modified):
    set_dot_notation(original, set_key, set_value)
    assert original == expected_modified


@pytest.mark.parametrize(
    "original, set_key, set_value",
    [
        param({"hello": 1}, "hello.foo", "world", id='do not overwrite non-dict-values'),
        param({"hello": {"world": {"this": {"is": "value"}}}}, "hello.world.this.is.value", 100),
    ],
)
def test_set_dot_notation_error(original, set_key, set_value):
    with pytest.raises(KeyError):
        set_dot_notation(original, set_key, set_value)
