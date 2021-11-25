import click

from tasdmc import fileio


def run_config_option(param_name: str):
    return click.option(
        '-r',
        '--run',
        param_name,
        required=True,
        type=click.Path(exists=True, resolve_path=True),
        help='main .yaml config file, see examples/run.yaml',
    )


def nodes_config_option(param_name: str):
    return click.option(
        '-n',
        '--nodes',
        param_name,
        required=True,
        type=click.Path(exists=True, resolve_path=True),
        help='nodes config file, see examples/nodes.yaml',
    )


def run_name_argument(param_name: str):
    def autocomplete(ctx, param, incomplete):
        return [run_name for run_name in fileio.get_all_run_names() if run_name.startswith(incomplete)]

    return click.argument(param_name, type=click.STRING, default="", shell_complete=autocomplete)
