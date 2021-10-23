"""Module for cleaning up any mess left from runs"""

from pathlib import Path
import click

from tasdmc import fileio


def get_failed_pipeline_files():
    return list(fileio.pipelines_failed_dir().glob('*.failed'))


def delete_all_files_from_failed_pipeline(pipeline_failed_path: Path):
    pipeline_id = pipeline_failed_path.name.replace('.failed', '')
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
    pipeline_failed_path.unlink()
