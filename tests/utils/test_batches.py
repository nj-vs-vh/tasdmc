import pytest

from typing import List

from tasdmc.utils import batches


@pytest.fixture
def collection() -> List[int]:
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


@pytest.mark.parametrize(
    "batch_size, expected_batches",
    [
        pytest.param(1, [[1], [2], [3], [4], [5], [6], [7], [8], [9], [10]]),
        pytest.param(2, [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]),
        pytest.param(3, [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]),
        pytest.param(10, [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]),
        pytest.param(15, [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]),
    ]
)
def test_batches(batch_size: int, expected_batches: List[List[int]], collection: List[int]):
    assert list(batches(collection, batch_size)) == expected_batches
