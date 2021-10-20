"""Progress monitoring module.

For now only incapsulates stdout displays with nice styling.

A system for process/node-distributed progress monitoring will be implemented in the future.
"""

import click
from datetime import datetime

from tasdmc import config


def _secho(msg: str, min_verbosity: int, **secho_kwargs):
    if config.verbosity() >= min_verbosity:
        msg = datetime.now().strftime(r"[%d/%m/%y %H:%M:%S]") + ' ' + msg
        click.secho(msg, **secho_kwargs)


def info(message: str):
    _secho(message, min_verbosity=1)


def debug(message: str):
    _secho(message, min_verbosity=2, dim=True)


def multiprocessing_debug(message: str):
    _secho(message, min_verbosity=2, dim=True)


def warning(message: str):
    _secho(message, min_verbosity=0, bold=True, fg='red')
