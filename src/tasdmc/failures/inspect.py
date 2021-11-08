import click
from pathlib import Path
import traceback
from enum import Enum

from typing import List

from tasdmc import fileio
from tasdmc.pipeline import standard_pipeline_steps
from tasdmc.config.internal import remove_config_key
from tasdmc.steps.exceptions import HashComputationFailed, FilesCheckFailed
from .utils import pipeline_id_from_failed_file



class StepStatus(Enum):
    OK = 'ok'
    CANT_SKIP = 'cant skip'
    READY_TO_RUN = 'ready to run'
    PENDING = 'pending'


status_chars = {
    StepStatus.OK: (click.style('✓', fg='green', bold=True), "Step was completed and can be skipped"),
    StepStatus.CANT_SKIP: (click.style("×", fg='red', bold=True), "Step was completed, but inputs have changed"),
    StepStatus.READY_TO_RUN: (click.style('⋯', fg='yellow', bold=True), "Step was not completed but is ready to run"),
    StepStatus.PENDING: (click.style("?", fg='yellow', bold=True), "Step was not completed, pending"),
}


def inspect_failed_pipelines(pipeline_failed_files: List[Path]):
    remove_config_key('debug')  # resetting debug to default to avoid appending to logs
    for pf in pipeline_failed_files:
        print_pipeline_steps(pipeline_id=pipeline_id_from_failed_file(pf))
    click.echo('\n Legend:')
    for char, descr in status_chars.values():
        click.echo(f"{char} {descr}")


def print_pipeline_steps(pipeline_id: str):
    click.secho(f"\n{pipeline_id}:", bold=True)
    pipeline_card_file = fileio.corsika_input_files_dir() / f"{pipeline_id}.in"
    if not pipeline_card_file.exists():
        click.echo("Can't find CORSIKA input card for pipeline!", fg='red', bold=True)
    pipeline_steps = standard_pipeline_steps(cards_generation_step=None, card_paths_override=[pipeline_card_file])

    for step in pipeline_steps:
        output_produced = step.output.files_were_produced()
        input_produced = step.input_.files_were_produced()
        try:
            input_hash_ok = step.input_.same_hash_as_stored()
            hash_computation_fail_msg = None
        except HashComputationFailed:
            input_hash_ok = False
            hash_computation_fail_msg = traceback.format_exc()

        if output_produced:
            if input_produced and input_hash_ok:
                status = StepStatus.OK
            else:
                status = StepStatus.CANT_SKIP
        else:
            if input_produced:
                status = StepStatus.READY_TO_RUN
            else:
                status = StepStatus.PENDING

        status_char = status_chars[status][0]
        click.echo(f'\t{status_char} {step.description}')
        if status is StepStatus.CANT_SKIP:
            if not input_produced:
                click.echo(
                    "\t* input files were never produced:\n"
                    + "\n".join([f"\t\t{f.relative_to(fileio.run_dir())}" for f in step.input_.must_exist])
                )
            if input_produced and not input_hash_ok:
                if hash_computation_fail_msg is None:
                    click.echo("\t* input files were produced, but their hashes are different from previously saved")
                else:
                    click.echo(f"\t* input files hash computation failed with error:\n{hash_computation_fail_msg}")
