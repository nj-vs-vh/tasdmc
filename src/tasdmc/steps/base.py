from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

from typing import List

from tasdmc import config, progress
from .exceptions import FilesCheckFailed


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.

    Subclassed by each step to incapsulate specific behavior and checks.
    """

    @property
    def must_exist(self) -> List[Path]:
        """List of file Paths that must exist for Files to be valid step output. Used in the default check method."""
        return []

    @property
    def not_retained(self) -> List[Path]:
        """List of file Paths that can be removed after they have been used in pipeline. This should include
        temporary or very large files, unnecessary for the end result.
        """
        return []

    def prepare_for_step_run(self):
        """Ensure that Files are ready to be created from scratch in a step.run(). For example, delete existing
        files if they can't be automatically overwritten during step run.
        
        May be overriden by subclasses.
        """
        pass

    def assert_files_are_ready(self):
        """Check Files if they are ready and raise FilesCheckFailes exception if there's a problem.
        
        Should not be overriden, but modified indirectly by overriding must_exist property and _check_contents method.
        """
        for f in self.must_exist:
            if not f.exists():
                raise FilesCheckFailed(f"{f} (and maybe others) do not exist")
        self._check_contents()

    def delete_not_retained_files(self):
        """Delete files that are not retained after pipeline end and create .deleted files in their place"""
        for f in self.not_retained:
            try:
                f.unlink()
                with open(str(f) + '.deleted', 'w') as del_f:
                    del_f.write(
                        f'THIS FILE INDICATES THAT THE FILE\n\n{f}\n\n'
                        + 'WAS PRODUCED AND THEN DELETED AFTER BEING USED IN A PIPELINE\n'
                    )
            except FileNotFoundError:
                pass


    def _check_contents(self):
        """Check Files' content, should be overriden by subclasses. Must raise FilesCheckFailed on errors."""
        pass

    def files_were_produced(self) -> bool:
        """Returns bool value indicating if Files' were already produced. This is not the same as check_if_ready
        as it also checks for files that may have been deleted because they are not retained.
        """
        try_checking_contents = True
        for f in self.must_exist:
            if not f.exists():
                if f in self.not_retained:  # maybe it was deleted? check if .deleted file exists
                    try_checking_contents = False  # but there's no point in checking contents anymore
                    if not Path(str(f) + '.deleted').exists():
                        return False
                else:
                    return False

        if try_checking_contents:
            try:
                self._check_contents()
            except FilesCheckFailed:            
                return False
        
        return True


@dataclass
class FileInFileOutStep(ABC):
    """Abstract class representing a single file-in-file-out operation in tasdmc pipeline"""

    input_: Files
    output: Files

    def run(self, force: bool = False):
        """Main method for running the step.

        Args:
            force (bool, optional): Skip output check and run case anyway. Defaults to False.
        """
        if not force and config.try_to_continue() and self.output.files_were_produced():
            progress.info(f"Skipping, output files found: {self.description}")
        else:
            self.input_.assert_files_are_ready()
            self.output.prepare_for_step_run()
            progress.info(f"Running: {self.description}")
            self._run()
            self.output.assert_files_are_ready()

    @property
    @abstractmethod
    def description(self) -> str:
        """Step description srting, used for progress monitoring"""
        pass

    def _run(self):
        """Internal method with 'bare' logic for funning the step, without input/output file checks,
        parallelization etc.

        Should be overriden by subclasses.
        """
        pass

    @classmethod
    def validate_config(self):
        """Validation of config values relevant to the step. May (and should) be overriden by subclasses"""
        pass
