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


@dataclass
class FileInFileOutStep(ABC):
    """Abstract class representing a single file-in-file-out operation in tasdmc pipeline"""

    @abstractmethod
    def run(self, *args, **kwargs):
        """Main method for running the step. Must be overriden by subclasses."""
        pass

    @classmethod
    def validate_config(self):
        """Validation of config values relevant to the step. May (and should) be overriden by subclasses"""
        pass


@dataclass
class FileInFileOutPipelineStep(FileInFileOutStep):
    """Abstract subclass representing a FileInFileOutStep as a part of pipeline. This means that it

    * can be run in parallel with other steps
    * checks input/output files before doing anything
    * maintains pipeline status in a dedicated file
    """

    input_: Files
    output: Files
    previous_step: Optional[FileInFileOutPipelineStep] = None

    @property
    def pipeline_id(self) -> str:
        """Any string uniquely identifying a pipeline (e.g. DATnnnnnn for standard pipeline).

        Must be overriden for the first step in the pipeline."""
        if self.previous_step is None:
            raise ValueError(f"No previous step found for {self.__class__.__name__}, can't get pipeline ID")
        else:
            return self.previous_step.pipeline_id

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
        futures_list.append(executor.submit(self.run, in_executor=True))

    def run(self, in_executor: bool = False):
        if in_executor:
            sleep(3 * random())  # in hopes of avoiding race condition for simultaneously running steps
            while not self.input_.files_were_produced() and not pipeline_progress.is_failed(self.pipeline_id):
                sleep_time = 60  # sec
                logs.multiprocessing_info(
                    f"Input files for '{self.description}' were not yet produced, sleeping for {sleep_time} sec"
                )
                sleep(sleep_time)

        if pipeline_progress.is_failed(self.pipeline_id):
            logs.multiprocessing_info(f"Not running '{self.description}', pipeline marked as failed")
            return
        else:
            logs.multiprocessing_info(f"Running '{self.description}'")

        try:
            if self.output.files_were_produced() and self.input_.same_hash_as_stored():
                step_progress.skipped(self)
            else:
                self.input_.assert_files_are_ready()
                self.output.prepare_for_step_run()
                step_progress.started(self)
                self._run()
                self.output.assert_files_are_ready()
                self.input_.store_contents_hash()
                step_progress.completed(self, output_size_mb=self.output.total_size('Mb'))
                self._post_run()
        except Exception as e:
            step_progress.failed(self, errmsg=str(e))
            pipeline_progress.mark_failed(
                self.pipeline_id,
                errmsg=(
                    f"Pipeline failed on step {self.__class__.__name__} ({self.input_.contents_hash}) "
                    + f"with traceback:\n\n{traceback.format_exc()}"
                ),
            )

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
