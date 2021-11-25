import click

from tasdmc import __version__


@click.group()
@click.version_option(__version__)
def cli():
    pass
