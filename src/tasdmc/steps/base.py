from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

from typing import List, Optional

from tasdmc import config, progress
from .exceptions import FilesCheckFailed


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.
    
    Subclassed by each step to incapsulate specific behavior and checks.
    """
    
    @property
    @abstractmethod
    def all(self) -> List[Path]:
        """List of all file Paths"""
        pass

    def clear(self):
        """Simply deletes all files. May be overriden by subclasses to contain additional logic."""
        for f in self.all:
            f.unlink(missing_ok=True)

    def check(self):
        """Check files, raise FilesCheckFailes exception if there's a problem"""
        for f in self.all:
            if not f.exists():
                raise FilesCheckFailed(f"{f} (and maybe others) do not exist")
        self._check_contents()

    def _check_contents(self):
        """Method to check file(s) content, may be overriden by subclasses.
        
        Must raise FilesCheckFailes on errors.
        """
        pass

    def check_passed(self) -> bool:
        """Like check, but return bool value of whether check was passed."""
        try:
            self.check()
            return True
        except FilesCheckFailed:
            return False


@dataclass
class FileInFileOutStep(ABC):
    """Abstract class representing a single file-in-file-out operation in tasdmc pipeline"""
    input_: Files
    output: Files

    def run(self):
        """Main method for running the step."""
        if config.try_to_continue() and self.output.check_passed():
            if self.description is not None:
                progress.info(f"Skipping, output files found: {self.description}")
        else:
            self.output.clear()
            if self.description is not None:
                progress.info(f"Running: {self.description}")
            self._run()
            self.output.check()

    @property
    def description(self) -> Optional[str]:
        """Optional step description srting, used for progress monitoring"""
        return None

    def _run(self):
        """Internal method with 'bare' logic for funning the step, without input/output file checks.
        
        Should be overriden by subclasses
        """
        pass

    @classmethod
    def validate_config(self):
        """Validation of config values relevant to the step. May (and should) be overriden by subclasses"""
        pass
