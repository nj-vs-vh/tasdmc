"""Command line interface used by click package to create `tasdmc` executable"""

import click
import tasdmc


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-r', '--run-config', default='run.yaml')
def run(run_config):
    config = tasdmc.read_config(run_config)
    tasdmc.prepare_run_dir(config)
    tasdmc.generate_corsika_input_files(config)
    tasdmc.run_simulation(config)
