import click

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
