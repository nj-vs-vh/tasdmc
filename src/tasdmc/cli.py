import click
import tasdmc


@click.group()
def cli():
    pass


@cli.command("run")
@click.option('-r', '--run-config', default='run.yaml')
def run(run_config):
    run_config_filename = run_config
    run_config = tasdmc.read_config(run_config_filename)
    tasdmc.prepare_run_dir(run_config, run_config_filename)
    tasdmc.generate_corsika_input_files(run_config)
