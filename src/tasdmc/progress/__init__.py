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


def info(message: str):
    click.secho(message)


def info_secondary(message: str):
    click.secho(message, dim=True)


# file logs


def _log_text_message(msg: str, log_filename: Path):
    with open(log_filename, 'a') as f:
        f.write(f"[{datetime2str(datetime.now())}] {msg}\n")


def multiprocessing_debug(message: str):
    message = f"(pid {os.getpid()}) {message}"
    _log_text_message(message, fileio.multiprocessing_debug_log())


def mark_pipeline_failed(pipeline_id: str, errmsg: str):
    fileio.pipeline_failed_file(pipeline_id).touch()  # this is atomic
    with open(fileio.pipeline_failed_file(pipeline_id), 'a') as f:
        f.write('\n' + errmsg + '\n')


def is_pipeline_failed(pipeline_id: str) -> bool:
    return fileio.pipeline_failed_file(pipeline_id).exists()
