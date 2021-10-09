"""Progress monitoring module.

For now only incapsulates stdout displays with nice styling.

A system for process/node-distributed progress monitoring will be implemented in the future.
"""

import click

from tasdmc import config


def title(message: str):
    if config.verbosity() > 0:
        click.secho('\n' + message + '\n', bold=True)


def info(message: str):
    if config.verbosity() > 0:
        click.secho(message)


def debug(message: str):
    if config.verbosity() > 1:
        click.secho(message, dim=True)


def warning(message: str):
    click.secho(message, bold=True, fg='red')
