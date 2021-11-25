import click

from tasdmc import system, pipeline, config, fileio
from tasdmc.utils import user_confirmation


def run_standard_pipeline_in_background(continuing: bool):
    system.run_in_background(pipeline.run_standard_pipeline, continuing)
    click.echo(f"Running in the background. Use 'tasdmc ps {config.run_name()}' to check run status")


def load_config_by_run_name(name: str) -> bool:
    run_config_path = None
    try:
        assert len(name), "No run name specified"
        run_config_path = fileio.get_run_config_path(name)
    except (AssertionError, ValueError) as exc:
        all_run_names = fileio.get_all_run_names()
        click.echo(f"{exc}, following runs exist:\n" + "\n".join([f"\t{r}" for r in all_run_names]))
        matching_run_names = [rn for rn in all_run_names if rn.startswith(name)]
        if len(matching_run_names) == 1:
            single_matching_run_name = matching_run_names[0]
            if user_confirmation(f"Did you mean '{single_matching_run_name}?'", yes='yes', no='no', default=True):
                click.echo()
                run_config_path = fileio.get_run_config_path(single_matching_run_name)
    if run_config_path is None:
        return False
    else:
        config.RunConfig.load(run_config_path)
        return True
