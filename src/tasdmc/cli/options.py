import click


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
