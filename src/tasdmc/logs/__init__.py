import os
from datetime import datetime
from pathlib import Path

from tasdmc import fileio

from .utils import datetime2str


# command-line messages


def system_resources_info(message: str):
    message = f"[{datetime2str(datetime.now())}] {message}"
    _log_text_message(message, fileio.system_resources_log())


def cards_generation_info(message: str):
    _log_text_message(message, fileio.cards_gen_info_log())


def multiprocessing_info(message: str):
    message = f"[{datetime2str(datetime.now())}] (pid {os.getpid()}) {message}"
    _log_text_message(message, fileio.multiprocessing_log())


def _log_text_message(msg: str, log_filename: Path):
    with open(log_filename, 'a') as f:
        f.write(msg + '\n')
