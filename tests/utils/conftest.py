import pytest
from pathlib import Path
from random import randint


CUR_DIR = Path(__file__).parent


@pytest.fixture
def temp_file() -> Path:
    fname = CUR_DIR / f"testing.{randint(0, 10 ** 6)}"
    fname.touch()
    yield fname
    fname.unlink()
