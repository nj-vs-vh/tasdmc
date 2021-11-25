"""Formatted logs printing"""

import os
from datetime import datetime
from pathlib import Path

from tasdmc import fileio

from .utils import datetime2str


def system_resources_info(message: str):
    message = f"[{datetime2str(datetime.now())}] {message}"
    _write_log_message(message, fileio.system_resources_log())


def cards_generation_info(message: str):
    _write_log_message(message, fileio.cards_gen_info_log())


def multiprocessing_info(message: str):
    message = f"[{datetime2str(datetime.now())}] (pid {os.getpid()}) {message}"
    _write_log_message(message, fileio.multiprocessing_log())


def input_hashes_debug(message: str):
    message = f"[{datetime2str(datetime.now())}] {message}"
    _write_log_message(message, fileio.input_hashes_debug_log())


def file_checks_debug(message: str):
    message = f"[{datetime2str(datetime.now())}] {message}"
    _write_log_message(message, fileio.file_checks_debug_log())


def _write_log_message(msg: str, log_filename: Path):
    with open(log_filename, 'a') as f:
        f.write(msg + '\n')
