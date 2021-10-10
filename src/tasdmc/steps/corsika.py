from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import corsika_wrapper as cw

from typing import List

from tasdmc import fileio, config, progress
from .base import Files, FileInFileOutStep
from .corsika_cards_generation import CorsikaCardsGenerationStep
from .exceptions import FilesCheckFailed
from .utils import check_particle_file_contents


@dataclass
class CorsikaCardFile(Files):
    infile: Path

    @property
    def all(self) -> List[Path]:
        return [self.infile]


@dataclass
class CorsikaOutputFiles(Files):
    particle: Path
    longtitude: Path
    stdout: Path
    stderr: Path

    @property
    def all(self) -> List[Path]:
        return [self.particle, self.longtitude, self.stderr, self.stdout]

    @classmethod
    def from_card_path(cls, card_path: Path) -> CorsikaOutputFiles:
        particle_file_path = fileio.corsika_output_files_dir() / card_path.stem
        return cls(
            particle_file_path,
            particle_file_path.with_suffix('.long'),
            particle_file_path.with_suffix('.stdout'),
            particle_file_path.with_suffix('.stderr'),
        )

    def check_contents(self):
        with open(self.stderr, 'r') as stderrfile:
            ignored_errmsg = 'Note: The following floating-point exceptions are signalling'
            error_messages = [line for line in stderrfile if not line.startswith(ignored_errmsg)]
            if len(error_messages) > 0:
                raise FilesCheckFailed(
                    f"{self.stderr.name} contains errors:\n" + '\n'.join([f'\t{line}' for line in error_messages])
                )
        MIN_CORSIKA_LONG_FILE_LINE_COUNT = 1500
        with open(self.longtitude, 'r') as longfile:
            line_count = len([line for line in longfile])
            if line_count < MIN_CORSIKA_LONG_FILE_LINE_COUNT:
                raise FilesCheckFailed(
                    f"{self.longtitude.name} seems too short! "
                    + f"Only {line_count} lines, but {MIN_CORSIKA_LONG_FILE_LINE_COUNT} expected."
                )
        with open(self.stdout, 'r') as stdoutfile:
            for line in stdoutfile:
                pass
            if not (isinstance(line, str) and 'END OF RUN' in line):
                raise FilesCheckFailed(f"{self.stdout.name} does not end with END OF RUN.")
        check_particle_file_contents(self.particle)


class CorsikaStep(FileInFileOutStep):
    input_: CorsikaCardFile
    output: CorsikaOutputFiles

    @classmethod
    def from_corsika_cards_generation(cls, corsika_cards_generation: CorsikaCardsGenerationStep) -> List[CorsikaStep]:
        input_files = corsika_cards_generation.output.files
        return [
            cls(input_=CorsikaCardFile(input_file), output=CorsikaOutputFiles.from_card_path(input_file))
            for input_file in input_files
        ]

    @property
    def description(self) -> str:
        return f"CORSIKA simulation on {self.input_.infile.name}"

    def _run(self):
        input_file = self.input_.infile
        progress.info(f"Running CORSIKA on {input_file.name}")
        cw.corsika(
            steering_card=cw.read_steering_card(input_file),
            # DATnnnnn.stdout and DATnnnnnn.stderr are created automatically by wrapper
            output_path=str(fileio.corsika_output_files_dir() / input_file.stem),
            corsika_path=config.get_key('corsika.path'),
            save_stdout=True,
        )

    @classmethod
    def validate_config(self):
        try:
            corsika_path = Path(config.get_key('corsika.path'))
            assert corsika_path.exists(), f"CORSIKA executable {corsika_path} does not exist"

            if config.get_key('corsika.default_executable_name', default=True):
                common_msg_end = (
                    ". This was inferred from CORSIKA executable name. "
                    + "If you use custom name, set corsika.default_executable_name to False."
                )
                # quick hacks relying on default CORSIKA naming strategy, not to be relied upon
                corsika_exe_name = corsika_path.name.lower()
                assert 'thin' in corsika_exe_name, (
                    "CORSIKA seems to be compiled without THINning option" + common_msg_end
                )
                low_E_hadr_model: str = config.get_key('corsika.low_E_hadronic_interactions_model')
                assert low_E_hadr_model.lower() in corsika_exe_name, "Low energy hadronic seems incorrect"
                high_E_hadr_model: str = config.get_key('corsika.high_E_hadronic_interactions_model')
                high_E_hadr_model_to_executable_name_part = {
                    'QGSJETII': 'QGSII',
                    'EPOS': 'EPOS',
                }
                assert (
                    high_E_hadr_model_to_executable_name_part[high_E_hadr_model].lower() in corsika_exe_name
                ), "High energy hadronic seems incorrect"
        except AssertionError as e:
            raise config.BadConfigValue(str(e))
