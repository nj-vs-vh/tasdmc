"""Progress monitoring module"""

import click
import os
from datetime import datetime
from pathlib import Path

from tasdmc import fileio

from .utils import datetime2str


# command-line messages


def warning(message: str):
    click.secho(message, bold=True, fg='red')


# file logs


def cards_generation_info(message: str):
    _log_text_message(message + '\n', fileio.cards_gen_info_log())


def multiprocessing_debug(message: str):
    message = f"[{datetime2str(datetime.now())}] (pid {os.getpid()}) {message}\n"
    _log_text_message(message, fileio.multiprocessing_debug_log())


def _log_text_message(msg: str, log_filename: Path):
    with open(log_filename, 'a') as f:
        f.write(msg)
