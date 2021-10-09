from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

from typing import List


class Files(ABC):
    """Abstract class for storing info on any set of files serving as inputs/outputs of tasdmc steps.
    
    Subclassed by each step to incapsulate specific behavior and checks.
    """
    
    @property
    @abstractmethod
    def all() -> List[Path]:
        pass

    def clear(self):
        for f in self.all:
            f.unlink(missing_ok=True)


@dataclass
class FileInFileOutStep(ABC):
    """Abstract class representing a single file-in-file-out operation in tasdmc pipeline"""
    input_: Files
    output: Files

    @abstractmethod
    def run(self):
        """Main method for running the step. Must be overriden by subclasses"""
        pass

    @classmethod
    def validate_config(self):
        """Validation of config values relevant to the step. May (and should) be overriden by subclasses"""
        pass
