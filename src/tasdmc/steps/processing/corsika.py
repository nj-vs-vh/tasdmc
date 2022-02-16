from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
from tempfile import TemporaryDirectory

from typing import List

from tasdmc import fileio, config
from tasdmc.steps.base import Files, PipelineStep, files_dataclass
from tasdmc.steps.exceptions import FilesCheckFailed
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty, check_last_line_contains
from tasdmc.subprocess_utils import execute_routine, Pipes, UnlimitedStackSize


@files_dataclass
class CorsikaCard(Files):
    card: Path


@files_dataclass
class CorsikaOutputFiles(Files):
    particle: Path
    longtitude: Path
    stdout: Path
    stderr: Path

    def prepare_for_step_run(self):
        for f in self.must_exist:  # corsika_wrapper do not overwrite files, so delete them manually
            f.unlink(missing_ok=True)

    @classmethod
    def from_corsika_card(cls, corsika_card: CorsikaCard) -> CorsikaOutputFiles:
        particle_file_path = fileio.corsika_output_files_dir() / corsika_card.card.stem
        return cls(
            particle_file_path,
            particle_file_path.with_suffix('.long'),
            particle_file_path.with_suffix('.stdout'),
            particle_file_path.with_suffix('.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(
            self.stderr, ignore_patterns=[r'Note: The following floating-point exceptions are signalling.*']
        )
        MIN_CORSIKA_LONG_FILE_LINE_COUNT = 1500
        with open(self.longtitude, 'r') as longfile:
            line_count = len([line for line in longfile])
            if line_count < MIN_CORSIKA_LONG_FILE_LINE_COUNT:
                raise FilesCheckFailed(
                    f"{self.longtitude.name} seems too short! "
                    + f"Only {line_count} lines, but {MIN_CORSIKA_LONG_FILE_LINE_COUNT} expected."
                )
        check_last_line_contains(self.stdout, 'END OF RUN')
        check_particle_file_contents(self.particle)


@dataclass
class CorsikaStep(PipelineStep):
    input_: CorsikaCard
    output: CorsikaOutputFiles

    @property
    def description(self) -> str:
        return f"CORSIKA simulation on {self.input_.card.name}"

    @property
    def pipeline_id(self) -> str:
        return self.output.particle.name

    @classmethod
    def from_corsika_cards(cls, corsika_card_paths: List[Path]) -> List[CorsikaStep]:
        inputs = [CorsikaCard(f) for f in corsika_card_paths]
        return [CorsikaStep(input_, CorsikaOutputFiles.from_corsika_card(input_)) for input_ in inputs]

    def _run(self):
        # inspiration and partial credit: https://github.com/fact-project/corsika_wrapper
        with TemporaryDirectory(prefix='corsika_') as tmp_dir:
            tmp_run_dir = Path(tmp_dir) / 'run'
            corsika_executable = Path(config.get_key('corsika.path'))
            shutil.copytree(corsika_executable.parent, tmp_run_dir, symlinks=False)
            tmp_corsika = tmp_run_dir / corsika_executable.name
            with UnlimitedStackSize(), Pipes(self.output.stdout, self.output.stderr) as (pipout, piperr):
                execute_routine(
                    executable=tmp_corsika,
                    global_=True,
                    args=[],
                    stdout=pipout,
                    stderr=piperr,
                    stdin_content=self.input_.card.read_text(),  # input cards are fed through stdin
                    run_from_directory=tmp_run_dir,  # CORSIKA needs to be launched from .../run/
                )

    @classmethod
    def validate_config(self):
        corsika_path = Path(config.get_key('corsika.path'))
        assert corsika_path.exists(), f"CORSIKA executable {corsika_path} not found"

        if config.get_key('corsika.default_executable_name', default=True):
            common_msg_end = (
                ". This was inferred from CORSIKA executable name. "
                + "If you use custom name, set corsika.default_executable_name to False."
            )
            # quick hacks relying on default CORSIKA naming strategy, not to be relied upon
            corsika_exe_name = corsika_path.name.lower()
            assert 'thin' in corsika_exe_name, "CORSIKA seems to be compiled without THINning option" + common_msg_end
            low_E_model: str = config.get_key('corsika.low_E_hadronic_interactions_model')
            if low_E_model == "FLUKA":
                assert (
                    os.environ.get("FLUPRO") is not None
                ), "FLUPRO environment variable must be defined when running CORSIKA with FLUKA model"
            assert (
                low_E_model.lower() in corsika_exe_name
            ), f"Low energy hadronic model mismatch (expected {low_E_model}, but executable name suggests otherwise)"
            high_E_model: str = config.get_key('corsika.high_E_hadronic_interactions_model')
            high_E_hadr_model_to_executable_name_part = {
                'QGSJETII': 'QGSII',
                'EPOS': 'EPOS',
            }
            assert (
                high_E_hadr_model_to_executable_name_part[high_E_model].lower() in corsika_exe_name
            ), f"High energy hadronic model mismatch (expected {high_E_model}, but executable name suggests otherwise)"
