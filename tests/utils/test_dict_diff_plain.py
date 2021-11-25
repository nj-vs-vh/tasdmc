import pytest
from pytest import param

from tasdmc.config.update import ConfigChange


@pytest.mark.parametrize(
    "old_dict, new_dict, expected_diff",
    [
        param(
            {"one": 1, "two": 2},
            {"one": 1, "two": 2, "three": 3},
            [("three", (None, 3))],
            id="simple value addition",
        ),
        param(
            {"one": 1},
            {"one": 1, "three": {"nested1": "hello", "nested2": "world"}},
            [("three.nested1", (None, "hello")), ("three.nested2", (None, "world"))],
            id="more complex value addition",
        ),
        param(
            {"one": 1, "top": {"hello": "world"}},
            dict(),
            [('one', (1, None)), ('top.hello', ('world', None))],
            id="complex value deletion",
        ),
        param(
            {"one": 1, "two": 2},
            {"one": "1", "two": "2"},
            [('one', (1, '1')), ('two', (2, '2'))],
            id="several values changed",
        ),
        param(
            {"top": {"list": [1, 3]}},
            {"top": {"list": [1, 2]}},
            [('top.list', ([1, 3], [1, 2]))],
            id="lists are not recursed into but treated as monolith values",
        ),
        param(
            {"top": {"list": [1]}},
            {"top": {"list": [2]}},
            [('top.list', ([1], [2]))],
            id="lists are not recursed into but treated as monolith values",
        ),
        param(
            {"top": {"list": [1, 2, 3, 4, 5]}},
            {"top": {"list": [1, 2, 3, 3, 5]}},
            [('top.list', ([1, 2, 3, 4, 5], [1, 2, 3, 3, 5]))],
            id="lists are not recursed into but treated as monolith values",
        ),
        param(
            {"top": {"list": [1, 2, 3]}},
            {"top": {"list": [1, 2, 3, 4]}},
            [('top.list', ([1, 2, 3], [1, 2, 3, 4]))],
            id="lists are not recursed into but treated as monolith values",
        ),
        param(
            {"top": {"list": [1, 2, 3]}},
            {"top": {"list": [1]}},
            [('top.list', ([1, 2, 3], [1]))],
            id="lists are not recursed into but treated as monolith values",
        ),
    ]
)
def test_dict_diff_plain(old_dict, new_dict, expected_diff):
    diff = list(ConfigChange.dict_diff_plain(old_dict, new_dict))
    assert diff == expected_diff
