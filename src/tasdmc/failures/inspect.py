from __future__ import annotations

import click
from pathlib import Path
import traceback
from enum import Enum
from dataclasses import dataclass

from typing import List, Tuple, Optional

from tasdmc import fileio
from tasdmc.utils import batches
from tasdmc.pipeline import standard_pipeline_steps
from tasdmc.config.internal import remove_config_key
from tasdmc.steps.exceptions import HashComputationFailed, FilesCheckFailed
from tasdmc.steps.utils import passed
from .utils import pipeline_id_from_failed_file

from tasdmc.steps.base import Files, FileInFileOutPipelineStep


class StepStatus(Enum):
    OK = (click.style('✓', fg='green', bold=True), "Step was completed and can be skipped")
    PENDING = (click.style("⋯", fg='yellow', bold=True), "Step was not completed, pending")
    PREV_STEP_RERUN_REQUIRED = (click.style("↑", fg='red', bold=True), "Step requires previous step's rerun")
    READY_TO_RUN = (click.style('↑', fg='yellow', bold=True), "Step was not completed but is ready to run")

    @property
    def char(self):
        return self.value[0]

    @property
    def description(self):
        return self.value[1]


@dataclass
class StepInspectionResult:
    inputs_were_produced: bool
    inputs_were_deleted: bool
    input_hash_ok: bool
    outputs_were_produced: bool
    input_hash_errmsg: Optional[str]

    @property
    def status(self) -> StepStatus:
        if not self.inputs_were_produced:
            return StepStatus.PENDING
        if self.input_hash_ok and self.outputs_were_produced:
            return StepStatus.OK
        if self.inputs_were_deleted:
            return StepStatus.PREV_STEP_RERUN_REQUIRED
        return StepStatus.READY_TO_RUN

    @classmethod
    def inspect(cls, step: FileInFileOutPipelineStep) -> StepInspectionResult:
        if step.input_.files_were_produced():
            input_produced = True
            input_deleted = passed(step.input_.assert_files_are_ready)
        else:
            input_produced, input_deleted = False, False

        try:
            input_hash_ok = step.input_.same_hash_as_stored()
            hash_computation_fail_msg = None
        except HashComputationFailed:
            input_hash_ok = False
            hash_computation_fail_msg = traceback.format_exc()

        return StepInspectionResult(
            input_produced,
            input_deleted,
            input_hash_ok,
            outputs_were_produced=step.output.files_were_produced(),
            input_hash_errmsg=hash_computation_fail_msg,
        )


def _print_legend():
    click.echo('\nLegend:')
    for s in StepStatus:
        click.echo(f"  {s.char}  {s.description}")


def inspect_failed_pipelines(pipeline_failed_files: List[Path], prompt_continue_each: int, fix: bool):
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
            click.echo('\nFailure reason:')
            click.secho(pf.read_text().strip(), dim=True)
            click.echo('\nSteps inspection:')
            inspect_pipeline_steps(pipeline_id, fix=fix)
        if prompt:
            _print_legend()
            click.echo("\nContinue? [Yes, no]")
            confirmation = input("> ")
            if confirmation == 'no':
                break


def inspect_pipeline_steps(pipeline_id: str, fix: bool = False):
    pipeline_card_file = fileio.corsika_input_files_dir() / f"{pipeline_id}.in"
    if not pipeline_card_file.exists():
        click.echo("Can't find CORSIKA input card for pipeline!", fg='red', bold=True)
    pipeline_steps = standard_pipeline_steps(cards_generation_step=None, card_paths_override=[pipeline_card_file])

    for step in pipeline_steps:
        inspection_result = StepInspectionResult.inspect(step)
        step_status = inspection_result.status
        click.echo(f'\t{step_status.char} {step.description}')
        if step_status is StepStatus.INPUTS_CHANGED:
            pass
            # if not input_produced:
            #     click.echo(
            #         "\t\t* input files were never produced:\n"
            #         + "\n".join([f"\t\t\t{f.relative_to(fileio.run_dir())}" for f in step.input_.must_exist])
            #     )
            # if input_produced and not input_hash_ok:
            #     if hash_computation_fail_msg is None:
            #         click.echo("\t\t* input file hashes have changed")
            #     else:
            #         click.echo(f"\t\t* input file hashes computation failed with error:\n{hash_computation_fail_msg}")

            #     try:
            #         step.input_.assert_files_are_ready()
            #         click.echo("\t\t* no fixing required, failure may be resolved on the next 'continue'")
            #     except FilesCheckFailed:  # input was produced, but is not ready = it was deleted because it is not retained
            #         outputs_to_clean = [s.output for s in step.previous_steps]
            #         if not fix:
            #             click.echo("\t\t* fixes required, pass --fix to clean these outputs:")
            #             click.echo("\n".join([f"\t\t\t{o}" for o in outputs_to_clean]))
            #         else:
            #             for o in outputs_to_clean:
            #                 click.echo(f"\t\t* cleaning {o}")
            #                 o.clean()
