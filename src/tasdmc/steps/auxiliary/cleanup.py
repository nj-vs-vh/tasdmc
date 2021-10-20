from __future__ import annotations
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from typing import List

from tasdmc.steps.base import Files, NotAllRetainedFiles, FileInFileOutPipelineStep


@dataclass
class FilesToDelete(NotAllRetainedFiles):
    files_to_delete: List[NotAllRetainedFiles]
    must_exist_files: Files

    @property
    def must_exist(self) -> List[Path]:
        return self.must_exist_files.must_exist

    @property
    def not_retained(self) -> List[Path]:
        return list(chain.from_iterable(o.not_retained for o in self.files_to_delete))


class NoFiles(Files):
    @property
    def all_files(self) -> List[Path]:
        return []

    def files_were_produced(self) -> bool:
        return False


@dataclass
class CleanupStep(FileInFileOutPipelineStep):
    input_: FilesToDelete
    output: NoFiles

    cleanup_steps: List[FileInFileOutPipelineStep] = None  # defaults are only to please dataclass defaults
    must_be_completed: FileInFileOutPipelineStep = None

    @classmethod
    def from_steps_to_cleanup(
        cls,
        cleanup_steps: List[FileInFileOutPipelineStep],
        must_be_completed: FileInFileOutPipelineStep,
    ) -> CleanupStep:
        return CleanupStep(
            input_=FilesToDelete(
                files_to_delete=[co.output for co in cleanup_steps if isinstance(co.output, NotAllRetainedFiles)],
                must_exist_files=must_be_completed.output,
            ),
            output=NoFiles(),
            cleanup_steps=cleanup_steps,
            must_be_completed=must_be_completed,
            previous_step=must_be_completed,
        )

    @property
    def description(self) -> str:
        return (
            "Deleting not retained outputs from following steps: "
            + f"{', '.join(list(set([s.__class__.__name__ for s in self.cleanup_steps])))}"
            + f" after {self.must_be_completed.__class__.__name__} is completed"
        )

    def _run(self):
        self.input_.delete_not_retained_files()
