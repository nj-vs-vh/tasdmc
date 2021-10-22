from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import corsika_wrapper as cw

from typing import List

from tasdmc import fileio, config
from tasdmc.steps.base import Files, FileInFileOutPipelineStep
from tasdmc.steps.corsika_cards_generation import CorsikaCardsGenerationStep, CorsikaCardFiles
from tasdmc.steps.exceptions import FilesCheckFailed
from tasdmc.steps.utils import check_particle_file_contents, check_file_is_empty, check_last_line_contains


@dataclass
class CorsikaCardFile(Files):
    card: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.card]

    @classmethod
    def from_corsika_card_files(cls, corsika_card_files: CorsikaCardFiles) -> List[CorsikaCardFile]:
        return [cls(card) for card in corsika_card_files.files]


@dataclass
class CorsikaOutputFiles(Files):
    particle: Path
    longtitude: Path
    stdout: Path
    stderr: Path

    @property
    def must_exist(self) -> List[Path]:
        return [self.particle, self.longtitude, self.stderr, self.stdout]

    def prepare_for_step_run(self):
        for f in self.must_exist:  # corsika_wrapper do not overwrite files, so delete them manually
            f.unlink(missing_ok=True)

    @classmethod
    def from_corsika_card_file(cls, corsika_card_file: CorsikaCardFile) -> CorsikaOutputFiles:
        particle_file_path = fileio.corsika_output_files_dir() / corsika_card_file.card.stem
        return cls(
            particle_file_path,
            particle_file_path.with_suffix('.long'),
            particle_file_path.with_suffix('.stdout'),
            particle_file_path.with_suffix('.stderr'),
        )

    def _check_contents(self):
        check_file_is_empty(
            self.stderr, ignore_strings=['Note: The following floating-point exceptions are signalling']
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


class CorsikaStep(FileInFileOutPipelineStep):
    input_: CorsikaCardFile
    output: CorsikaOutputFiles

    @property
    def description(self) -> str:
        return f"CORSIKA simulation on {self.input_.card.name}"

    @property
    def pipeline_id(self) -> str:
        return self.output.particle.name

    @classmethod
    def from_corsika_cards_generation(cls, corsika_cards_generation: CorsikaCardsGenerationStep) -> List[CorsikaStep]:
        inputs = CorsikaCardFile.from_corsika_card_files(corsika_cards_generation.output)
        return [CorsikaStep(input_, CorsikaOutputFiles.from_corsika_card_file(input_)) for input_ in inputs]

    def _run(self):
        input_file = self.input_.card
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
