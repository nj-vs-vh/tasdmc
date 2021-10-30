"""System-related actions module"""

import os

from typing import Callable, Any

from .processes import set_process_title, abort_run, process_alive, print_process_status


__all__ = [
    'set_process_title',
    'run_in_background',
    'abort_run',
    'process_alive',
    'print_process_status',
]


def run_in_background(background_fn: Callable[[Any], None], *background_fn_args: Any, keep_session: bool = False):
    child_pid = os.fork()
    if child_pid == 0:
        if not keep_session:
            os.setsid()  # creating new session for child process and hence detaching it from current terminal
        background_fn(*background_fn_args)
