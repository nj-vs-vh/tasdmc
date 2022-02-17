import click
import sys
import traceback

from tasdmc import pipeline, config, fileio
from tasdmc.utils import user_confirmation
from tasdmc.system import run_in_background


def run_simulation_in_background():
    run_in_background(pipeline.run_simulation)
    click.echo(f"Running in the background. Use 'tasdmc status {config.run_name()}' to check run status")


def _load_config_by_run_name(name: str) -> bool:
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
        if nodes_config_path.exists():
            config.NodesConfig.load(nodes_config_path)
        return True


def with_run_name_argument():
    def autocomplete(ctx, param, incomplete):
        return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]

    return click.argument("run_name", type=click.STRING, default="", shell_complete=autocomplete)


def loading_run_by_name(cmd_func):
    @with_run_name_argument()
    def wrapped_cmd_func(run_name: str, *args, **kwargs):
        if not _load_config_by_run_name(run_name):
            return
        cmd_func(*args, **kwargs)

    return wrapped_cmd_func


def error_catching(cmd_fn):
    def wrapped(*args, **kwargs):
        try:
            cmd_fn(*args, **kwargs)
        except Exception as e:
            click.secho(f"\n{e.__class__.__name__} exception raised: {e}\n\n", fg='red', bold=True, err=True)
            traceback.print_exc()
            sys.exit(1)

    return wrapped
