import click
from pathlib import Path
import traceback
from enum import Enum

from typing import List

from tasdmc import fileio
from tasdmc.utils import batches
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


def _print_legend():
    click.echo('\nLegend:')
    for char, descr in status_chars.values():
        click.echo(f"  {char}  {descr}")


def inspect_failed_pipelines(pipeline_failed_files: List[Path], prompt_continue_each: int):
    remove_config_key('debug')  # resetting debug to default to avoid appending to logs
    if prompt_continue_each == 0:
        prompt_continue_each = len(pipeline_failed_files)
        prompt = False
    else:
        prompt = True
    for page in batches(pipeline_failed_files, size=prompt_continue_each):
        for pf in page:
            pipeline_id = pipeline_id_from_failed_file(pf)
            click.secho(f"\n{pipeline_id}", bold=True)
            click.echo('Failure reason:')
            click.secho(pf.read_text(), dim=True)
            click.echo('Steps inspection:')
            print_pipeline_steps(pipeline_id=pipeline_id_from_failed_file(pf))
        if prompt:
            _print_legend()
            click.echo("\nContinue? [Yes, no]")
            confirmation = input("> ")
            if confirmation == 'no':
                break


def print_pipeline_steps(pipeline_id: str):
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
                    "\t\t* input files were never produced:\n"
                    + "\n".join([f"\t\t\t{f.relative_to(fileio.run_dir())}" for f in step.input_.must_exist])
                )
            if input_produced and not input_hash_ok:
                if hash_computation_fail_msg is None:
                    click.echo("\t\t* input file hashes do not match previously saved")
                else:
                    click.echo(f"\t\t* input file hashes computation failed with error:\n{hash_computation_fail_msg}")

