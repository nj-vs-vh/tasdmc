import click
import sys

from tasdmc import system, pipeline, config, fileio
from tasdmc.utils import user_confirmation


def run_standard_pipeline_in_background():
    system.run_in_background(pipeline.run_standard_pipeline)
    click.echo(f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status")


def load_config_by_run_name(name: str) -> bool:
    config_paths = None
    try:
        assert len(name), "No run name specified"
        config_paths = fileio.get_config_paths(name)
    except (AssertionError, ValueError) as exc:
        all_run_names = fileio.get_all_run_names()
        click.echo(f"{exc}, following runs exist:\n" + "\n".join([f"\t{r}" for r in all_run_names]))
        matching_run_names = [rn for rn in all_run_names if rn.startswith(name)]
        if len(matching_run_names) == 1:
            single_matching_run_name = matching_run_names[0]
            if user_confirmation(f"Did you mean '{single_matching_run_name}?'", yes='yes', no='no', default=True):
                click.echo()
                config_paths = fileio.get_config_paths(single_matching_run_name)
    if config_paths is None:
        return False
    else:
        run_config_path, nodes_config_path = config_paths
        config.RunConfig.load(run_config_path)
        if nodes_config_path.exists():  # in any given run this may (for distr. run) or may not (fot local run) exits
            config.NodesConfig.load(nodes_config_path)
        return True


def loading_run_by_name(cmd_func):
    def autocomplete(ctx, param, incomplete):
        return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]

    @click.argument("run_name", type=click.STRING, default="", shell_complete=autocomplete)
    def wrapped_cmd_func(run_name: str, *args, **kwargs):
        if not load_config_by_run_name(run_name):
            return
        cmd_func(*args, **kwargs)

    return wrapped_cmd_func


def error_catching(cmd_fn):
    def wrapped(*args, **kwargs):
        try:
            cmd_fn(*args, **kwargs)
        except Exception as e:
            click.secho(str(e), fg='red', bold=True, err=True)
            sys.exit(1)

    return wrapped
