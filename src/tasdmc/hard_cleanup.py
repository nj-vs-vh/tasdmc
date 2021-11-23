from pathlib import Path
import click

from typing import List

from tasdmc import fileio, config
from tasdmc.utils import user_confirmation_destructive


def delete_all_pipelines(pipeline_ids: List[Path]):
    click.echo(
        f"Failed pipelines will be {click.style('completely', bold=True)} removed:\n"
        + "\n".join([f'\t{pid}' for pid in pipeline_ids])
    )
    click.echo(f"You may want to first inspect these pipelines with 'tasdmc inspect {config.run_name()} --failed'")
    if user_confirmation_destructive(config.run_name()):
        for pipeline_id in pipeline_ids:
            click.echo(f"Cleaning up files for {pipeline_id}")
            for dir in [
                fileio.corsika_input_files_dir(),
                fileio.corsika_output_files_dir(),
                fileio.dethinning_output_files_dir(),
                fileio.c2g_output_files_dir(),
            ]:
                for file in dir.glob(pipeline_id + '*'):
                    click.secho(f"\t{file}", dim=True)
                    file.unlink()
            fileio.pipeline_failed_file(pipeline_id).unlink(missing_ok=True)
    else:
        click.echo("Maybe next time...")
