from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from time import sleep
from concurrent.futures import Future
import traceback
from random import random

from typing import Optional, List

from tasdmc import logs
from tasdmc.logs import step_progress, pipeline_progress
from .files import Files
from .step_status_shared import StepRuntimeStatus


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
                f"No previous steps found for {self.__class__.__name__}, can't get pipeline ID; "
                + "Override pipeline_id property or specify previous steps"
            )
        else:
            return self.previous_steps[0].pipeline_id

    @property
    def id_(self):
        return f'{self.__class__.__name__}:{self.input_.id_}:{self.output.id_}'

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
        # waiting for previous steps to complete
        waiting_msg_logged = False
        while True:
            if self.previous_steps is None:  # the first step in a pipeline
                break
            previous_step_statuses = [ps.runtime_status for ps in self.previous_steps]
            if any(s is StepRuntimeStatus.FAILED for s in previous_step_statuses):
                logs.multiprocessing_info(f"Exiting '{self.description}' one of its previous steps has failed")
                return
            if all(s is StepRuntimeStatus.COMPLETED for s in previous_step_statuses):
                break
            if not waiting_msg_logged:
                logs.multiprocessing_info(f"Steps previous to '{self.description}' aren't completed, waiting")
                waiting_msg_logged = True
            sleep(5)  # checked each 5 seconds

        if pipeline_progress.is_failed(self.pipeline_id):
            logs.multiprocessing_info(f"Exiting '{self.description}', pipeline marked as failed")
            return

        # pipeline integrity check
        if self.previous_steps is not None:
            previous_steps: List[PipelineStep] = self.previous_steps
            if not all(previous_step.output.files_were_produced() for previous_step in previous_steps):
                pipeline_progress.mark_failed(
                    self.pipeline_id,
                    errmsg=(
                        f"Pipeline configuration error in {self.id_}\n\n"
                        + f"Previous steps were completed, but not all their outputs are produced:\n"
                        + "\n".join([f"\t{s.output}" for s in previous_steps])
                    ),
                )
                return
            if not self.input_.files_were_produced():
                pipeline_progress.mark_failed(
                    self.pipeline_id,
                    errmsg=(
                        f"Pipeline configuration error in {self.id_}\n\n"
                        + f"Previous steps were completed, their outputs produced:\n"
                        + "\n".join([f"\t{s.output}" for s in previous_steps])
                        + f"\nBut this step's input is not:\n\t{self.input_}"
                    ),
                )
                return

        # actual step run
        logs.multiprocessing_info(f"Entering '{self.description}'")
        try:
            if self.output.files_were_produced() and self.input_.same_hash_as_stored():
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
        except Exception as e:
            step_progress.failed(self, errmsg=str(e))
            pipeline_progress.mark_failed(
                self.pipeline_id,
                errmsg=(
                    f"Pipeline failed on step {self.__class__.__name__} ({self.input_.contents_hash}) "
                    + f"with traceback:\n\n{traceback.format_exc()}"
                ),
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
