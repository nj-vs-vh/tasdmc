from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from time import sleep
from concurrent.futures import Future
import traceback

from typing import Optional, List

from tasdmc import logs, config
from tasdmc.logs import step_progress, pipeline_progress
from .files import Files
from .step_status_shared import StepRuntimeStatus


class StepFailedException(Exception):
    pass


@dataclass
class PipelineStep(ABC):
    """Abstract class representing a file-in-file-out step in a simulation pipeline.

    * can be run in parallel with other steps
    * checks input/output files before doing anything
    * reports pipeline failure to a dedicated file
    """

    input_: Files
    output: Files
    previous_steps: Optional[List[PipelineStep]] = None
    _step_status_index_in_shared_array: Optional[int] = None

    @property
    def pipeline_id(self) -> str:
        """A string uniquely identifying a pipeline (a set of sequential steps). Example is 'DATnnnnnn'
        for standard simulation.

        Must be overriden for the first step in the pipeline."""
        if not self.previous_steps:
            raise ValueError(
                f"No previous steps found for {self.name}, can't get pipeline ID; "
                + "Override pipeline_id property or specify previous steps"
            )
        else:
            return self.previous_steps[0].pipeline_id

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.get_id()

    def get_id(self) -> str:
        return f'{self.name}:{self.input_.get_id()}:{self.output.get_id()}'

    def set_index(self, i: int):
        self._step_status_index_in_shared_array = i

    @property
    def runtime_status(self) -> StepRuntimeStatus:
        return StepRuntimeStatus.load(self._step_status_index_in_shared_array)

    def save_runtime_status(self, status: StepRuntimeStatus):
        status.save(self._step_status_index_in_shared_array)

    @property
    @abstractmethod
    def description(self) -> str:
        """Step description string, used for logging"""
        pass

    def schedule(self, executor: ProcessPoolExecutor, futures_list: List[Future]) -> Future:
        """Main method to schedule step's execution in multiprocessing pool

        Args:
            executor (ProcessPoolExecutor): ProcessPoolExecutor to submit step to
            futures_list (list of Future): list of futures to add this run future result into
        """
        assert (
            self._step_status_index_in_shared_array is not None
        ), f"Step status index was not assigned for '{self.description}'!"
        futures_list.append(executor.submit(self.run_in_executor))

    def run_in_executor(self):
        try:
            if config.Ephemeral.safe_abort_in_progress:
                # exiting as if step has not been started at all
                return
            if self.previous_steps is not None:  # not the first step in a pipeline
                # waiting for previous steps to complete
                waiting_msg_logged = False
                while True:
                    previous_step_statuses = [ps.runtime_status for ps in self.previous_steps]
                    if any(s is StepRuntimeStatus.FAILED for s in previous_step_statuses):
                        logs.multiprocessing_info(f"Exiting '{self.description}' one of its previous steps has failed")
                        raise StepFailedException()
                    if all(s is StepRuntimeStatus.COMPLETED for s in previous_step_statuses):
                        break
                    if not waiting_msg_logged:
                        logs.multiprocessing_info(f"Steps previous to '{self.description}' aren't completed, waiting")
                        waiting_msg_logged = True
                    sleep(1)  # checked each second

                # pipeline integrity check
                previous_steps: List[PipelineStep] = self.previous_steps
                if not all(previous_step.output.files_were_produced() for previous_step in previous_steps):
                    pipeline_progress.mark_failed(
                        self.pipeline_id,
                        errmsg=(
                            f"Pipeline configuration error in {self}\n\n"
                            + f"Previous steps were completed, but not all their outputs are produced:\n"
                            + "\n".join([f"\t{s.output}" for s in previous_steps])
                        ),
                    )
                    raise StepFailedException()
                if not self.input_.files_were_produced():
                    pipeline_progress.mark_failed(
                        self.pipeline_id,
                        errmsg=(
                            f"Pipeline configuration error in {self}\n\n"
                            + f"Previous steps were completed, their outputs produced:\n"
                            + "\n".join([f"\t{s.output}" for s in previous_steps])
                            + f"\nBut this step's input is not:\n\t{self.input_}"
                        ),
                    )
                    raise StepFailedException()

            # actual step run
            logs.multiprocessing_info(f"{self.description}")
            try:
                force_rerun = self.name in config.get_key("debug.force_rerun_steps", default=[])
                trying_to_skip = not force_rerun and self.output.files_were_produced()
                if config.Ephemeral.rerun_step_on_input_hash_mismatch:
                    # with this option on hash mismatch go to the actual run if arm
                    trying_to_skip = trying_to_skip and self.input_.same_hash_as_stored()
                if trying_to_skip:
                    if not self.input_.same_hash_as_stored():
                        self.input_.same_hash_as_stored(force_log=True)
                        raise StepFailedException(
                            f"Input hash mismatch for {self.input_}, see input_hashes_debug.log.\n"
                            + "To fix this error, run continue with --rerun-step-on-input-hash-mismatch or "
                            + "--disable-input-hash-checks flag."
                        )
                    step_progress.skipped(self)
                else:
                    step_progress.started(self)
                    self.input_.assert_files_are_ready()
                    self.output.prepare_for_step_run()
                    self.input_.store_contents_hash()
                    self._run()
                    assert self.input_.same_hash_as_stored(), "Input hash changed while step was running"
                    self.output.assert_files_are_ready()
                    self._post_run()
                    step_progress.completed(self, output_size_mb=self.output.total_size('Mb'))

                self.save_runtime_status(StepRuntimeStatus.COMPLETED)
            except Exception as e:  # step execution and/or io files error
                step_progress.failed(self, errmsg=str(e))
                pipeline_progress.mark_failed(
                    self.pipeline_id,
                    errmsg=f"Pipeline failed on {self} with traceback:\n\n{traceback.format_exc()}",
                )
                raise StepFailedException()
        except Exception as e:  # any other error during waiting/pipeline integrity check/whatever
            if not isinstance(e, StepFailedException):
                pipeline_progress.mark_failed(
                    self.pipeline_id,
                    errmsg=f"Pipeline failed on {self} with unexpected exception {e} ({e.__class__.__name__})",
                )
            self.save_runtime_status(StepRuntimeStatus.FAILED)

    @abstractmethod
    def _run(self):
        """Internal method with 'bare' logic for running the step, without input/output file checks,
        parallelization etc.

        Must be overriden by subclasses.
        """
        pass

    def _post_run(self):
        """Internal method for post-run cleanup.

        May be overriden by subclasses.
        """
        pass

    @classmethod
    def validate_config(self):
        """Validation of config values relevant to the step. May (and should) be overriden by subclasses"""
        pass
