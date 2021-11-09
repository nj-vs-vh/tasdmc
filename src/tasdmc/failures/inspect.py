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
    PENDING = (click.style("⋯", fg='yellow', bold=True), "Step pending, inputs were not produced")
    RERUN_REQUIRED = (click.style('↑', fg='yellow', bold=True), "Step requires rerun")
    PREV_STEP_RERUN_REQUIRED = (click.style("↑", fg='red', bold=True), "Step requires previous step's rerun")

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
    input_check_failed_errmsg: Optional[str]
    outputs_were_produced: bool
    outputs_were_deleted: bool
    output_check_failed_errmsg: Optional[str]
    input_hash_ok: bool
    input_hash_errmsg: Optional[str]

    @property
    def status(self) -> StepStatus:
        if not self.inputs_were_produced:
            return StepStatus.PENDING
        if self.input_hash_ok and self.outputs_were_produced:
            return StepStatus.OK
        if self.inputs_were_deleted:
            return StepStatus.PREV_STEP_RERUN_REQUIRED
        else:
            return StepStatus.RERUN_REQUIRED

    @staticmethod
    def files_produced_deleted_errmsg(files: Files) -> Tuple[bool, bool, Optional[str]]:
        if files.files_were_produced():
            produced = True
            try:
                files.assert_files_are_ready()
                deleted = False
                check_failed_errmsg = None
            except FilesCheckFailed:
                deleted = True
                check_failed_errmsg = traceback.format_exc()
        else:
            produced, deleted = False, False
        return produced, deleted, check_failed_errmsg

    @classmethod
    def inspect(cls, step: FileInFileOutPipelineStep) -> StepInspectionResult:
        inputs_produced, inputs_deleted, inputs_check_failed_errmsg = cls.files_produced_deleted_errmsg(step.input_)
        outputs_produced, outputs_deleted, outputs_check_failed_errmsg = cls.files_produced_deleted_errmsg(step.output)

        try:
            input_hash_ok = step.input_.same_hash_as_stored()
            hash_computation_fail_msg = None
        except HashComputationFailed:
            input_hash_ok = False
            hash_computation_fail_msg = traceback.format_exc()

        return StepInspectionResult(
            inputs_were_produced=inputs_produced,
            inputs_were_deleted=inputs_deleted,
            input_check_failed_errmsg=inputs_check_failed_errmsg,
            outputs_were_produced=outputs_produced,
            outputs_were_deleted=outputs_deleted,
            output_check_failed_errmsg=outputs_check_failed_errmsg,
            input_hash_ok=input_hash_ok,
            input_hash_errmsg=hash_computation_fail_msg,
        )


def _print_legend():
    click.echo('\nLegend:')
    for s in StepStatus:
        click.echo(f"  {s.char}  {s.description}")


def inspect_failed_pipelines(pipeline_failed_files: List[Path], page_size: int, fix: bool, verbose: bool):
    remove_config_key('debug')  # resetting debug to default to avoid appending to logs
    if page_size == 0:
        page_size = len(pipeline_failed_files)
        prompt = False
    else:
        prompt = page_size < len(pipeline_failed_files)
    for page_num, page in enumerate(batches(pipeline_failed_files, size=page_size)):
        click.echo(
            f"Failed pipelines {((1 + page_num) - 1) * page_size} - {(1 + page_num) * page_size - 1} "
            + f"(of {len(pipeline_failed_files)})"
        )
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


def inspect_pipeline_steps(pipeline_id: str, fix: bool = False, verbose: bool = False):
    pipeline_card_file = fileio.corsika_input_files_dir() / f"{pipeline_id}.in"
    if not pipeline_card_file.exists():
        click.echo("Can't find CORSIKA input card for pipeline!", fg='red', bold=True)
    pipeline_steps = standard_pipeline_steps(cards_generation_step=None, card_paths_override=[pipeline_card_file])

    for step in pipeline_steps:
        step_inspection = StepInspectionResult.inspect(step)
        step_status = step_inspection.status
        _echo_indented(f'{step_status.char} {step.description}', indent=1)
        if not verbose:
            continue
        if step_status is StepStatus.PREV_STEP_RERUN_REQUIRED:
            outputs_to_clean = [s.output for s in step.previous_steps]
            if not fix:
                _echo_indented("* pass --fix to clean following outputs:", indent=2)
                _echo_indented("\n".join([f"{o}" for o in outputs_to_clean]), indent=3, multiline=True)
            else:
                _echo_indented("* cleaning outputs", indent=2)
                for o in outputs_to_clean:
                    _echo_indented(f"* cleaning {o}", indent=3)
                    o.clean()
        if step_status is StepStatus.RERUN_REQUIRED:
            if not step_inspection.input_hash_ok:
                if step_inspection.input_hash_errmsg is not None:
                    _echo_indented("* input hash check failed:", indent=2)
                    _echo_indented(step_inspection.input_hash_errmsg, indent=3, multiline=True)
                else:
                    _echo_indented("* input hash doesn't match with the saved value", indent=2)
            if not step_inspection.outputs_were_produced:
                _echo_indented("* outputs were not produced or didn't pass checks:", indent=2)
                if step_inspection.output_check_failed_errmsg is not None:
                    _echo_indented(step_inspection.output_check_failed_errmsg, indent=3, multiline=True)
                else:
                    _echo_indented("* no error message available", indent=3)


def _echo_indented(msg: str, indent: int, multiline: bool = False, **click_secho_kwargs):
    msg_lines = [msg] if not multiline else msg.splitlines()
    for line in msg_lines:
        click.secho(("\t" * indent) + line, **click_secho_kwargs)
