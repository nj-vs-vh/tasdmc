from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from time import sleep

from typing import Optional

from tasdmc import config, progress
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
        """Step description string, used for progress monitoring"""
        pass

    def run(self, executor: Optional[ProcessPoolExecutor] = None):
        """Main method for running the step.

        Args:
            executor (ProcessPoolExecutor, optional): If specified, step is run inside executor, e.g. in a
                                                      dedicated process. Defaults to None (run in the main process).
        """

        def run_step(in_separate_process: bool = False):
            if in_separate_process:
                while not self.input_.files_were_produced():
                    sleep_time = 30  # sec
                    progress.multiprocessing_debug(
                        f"Input files for '{self.description}' were not yet produced, sleeping for {sleep_time} sec"
                    )
                    sleep(sleep_time)

            if config.try_to_continue() and self.input_.same_hash_as_stored() and self.output.files_were_produced():
                progress.info(f"Skipping: {self.description}")
            else:
                self.input_.assert_files_are_ready()
                self.output.prepare_for_step_run()
                progress.info(f"Running: {self.description}")
                self._run()
                self.output.assert_files_are_ready()
                self.input_.store_contents_hash()
                progress.debug(f"Output files from '{self.description}' size: {self.output.total_size('Mb')} Mb")

        if executor is None:
            run_step(in_separate_process=False)
        else:
            executor.submit(run_step, in_separate_process=True)

    @abstractmethod
    def _run(self):
        """Internal method with 'bare' logic for running the step, without input/output file checks,
        parallelization etc.

        Must be overriden by subclasses.
        """
        pass