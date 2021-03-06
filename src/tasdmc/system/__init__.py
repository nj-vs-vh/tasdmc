"""System-related actions module"""

import os

from typing import Callable, Any


def run_in_background(
    background_fn: Callable[[Any], None], *background_fn_args: Any, keep_session: bool = False
) -> int:
    child_pid = os.fork()
    if child_pid == 0:
        if not keep_session:
            os.setsid()  # creating new session for child process and hence detaching it from current terminal
        background_fn(*background_fn_args)
    return child_pid
