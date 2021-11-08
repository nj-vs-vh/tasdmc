import click
from pathlib import Path

from typing import List

from tasdmc import fileio
from tasdmc.pipeline import standard_pipeline_steps
from .utils import pipeline_id_from_failed_file


def inspect_failed_pipelines(pipeline_failed_files: List[Path]):
    for pf in pipeline_failed_files:
        print_pipeline_steps(pipeline_id=pipeline_id_from_failed_file(pf))


def print_pipeline_steps(pipeline_id: str):
    click.secho(f"\n{pipeline_id}:", bold=True)
    pipeline_card_file = fileio.corsika_input_files_dir() / f"{pipeline_id}.in"
    pipeline_steps = standard_pipeline_steps(cards_generation_step=None, card_paths_override=[pipeline_card_file])
    for step in pipeline_steps:
        click.echo('\t' + step.description)
