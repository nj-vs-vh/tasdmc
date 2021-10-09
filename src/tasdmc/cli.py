"""Command line interface used by click package to create `tasdmc` executable"""

import click
import tasdmc


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-c', '--config', default='run.yaml')
def run(config):
    tasdmc.config.load(config)
    tasdmc.prepare_run_dir()
    tasdmc.generate_corsika_input_files()
    tasdmc.run_simulation()
