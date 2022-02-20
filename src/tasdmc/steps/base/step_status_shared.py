from __future__ import annotations

from enum import Enum
import multiprocessing as mp

from typing import Optional


# array of ints, 0 for pending, 1 for completed, 2 for error
STEP_STATUSES_SHARED: Optional[mp.Array] = None


class StepRuntimeStatus(Enum):
    PENDING = 0
    COMPLETED = 1
    FAILED = 2

    @classmethod
    def load(cls, idx: int) -> StepRuntimeStatus:
        if STEP_STATUSES_SHARED is None:
            raise ValueError("STEP_STATUSES_SHARED array was not initialized")
        with STEP_STATUSES_SHARED.get_lock():
            return StepRuntimeStatus(STEP_STATUSES_SHARED[idx])

    def save(self, idx: int):
        if STEP_STATUSES_SHARED is None:
            raise ValueError("STEP_STATUSES_SHARED array was not initialized")
        with STEP_STATUSES_SHARED.get_lock():
            STEP_STATUSES_SHARED[idx] = self.value


def set_step_statuses_array(arr: mp.Array):
    global STEP_STATUSES_SHARED
    STEP_STATUSES_SHARED = arr
