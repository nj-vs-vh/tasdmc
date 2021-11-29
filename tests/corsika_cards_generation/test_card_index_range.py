import pytest
from pytest import param
from pytest_mock import MockerFixture

from tasdmc.steps.corsika_cards_generation import card_index_range_from_config


@pytest.mark.parametrize(
    "subset_config, cards_count, expected_range",
    [
        param(None, 1000, range(1000)),
        param({"all_weights": [1, 1], "this_idx": 0}, 100, range(0, 50)),
        param({"all_weights": [1, 1], "this_idx": 1}, 100, range(50, 100)),
        param({"all_weights": [1, 1, 1], "this_idx": 2}, 100, range(66, 100)),
        param({"all_weights": [1, 2, 1], "this_idx": 1}, 100, range(25, 75)),
        param({"all_weights": [1, 2, 1], "this_idx": 1}, 10, range(3, 7)),
    ]
)
def test_card_index_range(subset_config, cards_count, expected_range, mocker: MockerFixture):
    mocker.patch("tasdmc.config.get_key", return_value=subset_config)
    assert list(card_index_range_from_config(cards_count)) == list(expected_range)
