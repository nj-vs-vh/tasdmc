"""Throwing CORSIKA-generated showers onto an SD grid, taking calibration into account"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from functools import lru_cache
import random
from datetime import datetime

from typing import List, Dict, Iterable, Tuple

from tasdmc import fileio, config
from tasdmc.steps.base import Files, FileInFileOutPipelineStep
from tasdmc.steps.exceptions import FilesCheckFailed, BadDataFiles
from .corsika2geant import C2GOutputFiles, Corsika2GeantStep
from .tothrow_generation import TothrowFile, TothrowGenerationStep

from tasdmc.c_routines_wrapper import test_sdmc_spctr_runnable, run_sdmc_spctr, set_limits_for_sdmc_spctr


@dataclass
class C2GOutputWithTothrowFiles(Files):
    c2g_output: C2GOutputFiles
    tothrow: TothrowFile

    @property
    def all_files(self) -> List[Path]:
        return self.c2g_output.all_files + self.tothrow.all_files

    @property
    def must_exist(self) -> List[Path]:
        return self.c2g_output.must_exist + self.tothrow.must_exist

    def _check_contents(self):
        showlib_file, _ = self.tothrow.get_showlib_and_nparticles()
        if showlib_file != self.c2g_output.tile:
            raise FilesCheckFailed(
                f"Tothrow file '{self.tothrow.tothrow}' has showlib field ({showlib_file}) "
                + f"that do not match with the tile file {self.c2g_output.tile}"
            )


@dataclass
class EventFiles(Files):
    dst_files_by_epoch: Dict[int, Path]
    stdout: Path
    stderr: Path
    calibration_files_by_epoch: Dict[int, Path]

    @classmethod
    def from_input(cls, input_files: C2GOutputWithTothrowFiles) -> EventFiles:
        calibration_by_epoch = _get_calibration_files_by_epoch()
        corsika_event_name = input_files.c2g_output.corsika_event_name
        return EventFiles(
            dst_files_by_epoch={
                epoch: fileio.events_dir() / f'{corsika_event_name}_{epoch}.dst.gz'
                for epoch in calibration_by_epoch.keys()
            },
            stdout=fileio.events_dir() / f'{corsika_event_name}.events.stdout',
            stderr=fileio.events_dir() / f'{corsika_event_name}.events.stderr',
            calibration_files_by_epoch=calibration_by_epoch,
        )

    def prepare_for_step_run(self):
        with open(self.stdout, 'a') as f:
            f.write(f"\n\n{'='*100}\nEVENT GENERATION LOG; STARTED AT {datetime.utcnow().isoformat()}\n{'='*100}\n\n")
        self.stderr.unlink(missing_ok=True)

    def iterate_epochs(self) -> Iterable[Tuple[int, Path, Path]]:
        return (
            (epoch, self.dst_files_by_epoch[epoch], self.calibration_files_by_epoch[epoch])
            for epoch in sorted(self.calibration_files_by_epoch.keys())
        )

    @property
    def must_exist(self) -> List[Path]:
        return [self.stdout, self.stderr, *self.dst_files_by_epoch.values()]


class EventsGenerationStep(FileInFileOutPipelineStep):
    input_: C2GOutputWithTothrowFiles
    output: EventFiles

    @property
    def description(self) -> str:
        return f"Throwing CORSIKA events on SD grid for input TBD"

    @classmethod
    def from_corsika2geant_with_tothrow(
        cls, c2g_step: Corsika2GeantStep, tothrow_step: TothrowGenerationStep
    ) -> EventsGenerationStep:
        input_ = C2GOutputWithTothrowFiles(c2g_step.output, tothrow_step.output)
        return EventsGenerationStep(input_=input_, output=EventFiles.from_input(input_), previous_step=tothrow_step)

    def _run(self):
        set_limits_for_sdmc_spctr()
        n_try = _n_try_from_config()
        smear_energies = _smear_energies_from_config()
        _, n_particles_per_epoch = self.input_.tothrow.get_showlib_and_nparticles()
        for epoch, event_file, sdcalib_file in self.output.iterate_epochs():
            # TODO: check if event file already exists here!
            with open(self.output.stdout, 'a') as f:
                f.write(
                    f'\nGENERATING EVENTS FOR EPOCH {epoch}\n'
                    + f'{n_particles_per_epoch} events, calibration file {sdcalib_file.name}\n'
                )
            for i_try in range(1, n_try + 1):
                with open(self.output.stdout, 'a') as f:
                    f.write(f'\nATTEMPT {i_try}/{n_try}\n')
                if run_sdmc_spctr(
                    self.input_.c2g_output.tile,
                    event_file,
                    n_particles_per_epoch,
                    random.randint(1, int(1e6)),
                    epoch,
                    sdcalib_file,
                    smear_energies,
                    # TODO: azi.txt file may be specified here
                    self.output.stdout,
                    self.output.stderr,
                ):
                    break
            else:  # when not broke out of the loop
                with open(self.output.stderr, 'a') as f:
                    f.write(f'\nFAILED AFTER {n_try} ATTEMPTS')

    @classmethod
    def validate_config(cls):
        set_limits_for_sdmc_spctr()
        test_sdmc_spctr_runnable()
        _n_try_from_config()
        _smear_energies_from_config()
        assert fileio.DataFiles.atmos.exists(), "atmos.bin file not found!"
        _get_calibration_files_by_epoch()


def _n_try_from_config() -> int:
    n_try = int(config.get_key("throwing.sdmc_spctr_n_try", default=10))
    assert n_try > 0, f"throwing.sdmc_spctr_n_try must be non-negative int, but {n_try} given"
    return n_try


def _smear_energies_from_config() -> bool:
    return bool(config.get_key("throwing.smear_events_in_bin", default=True))


@lru_cache(1)
def _get_calibration_files_by_epoch() -> Dict[int, Path]:
    calibration_dirname = str(config.get_key("throwing.calibration_dir"))
    calibration_dir = config.Global.data_dir / calibration_dirname
    if not calibration_dir.exists():
        raise BadDataFiles(
            f"Specified calibration directory {calibration_dirname} does not exist in {config.Global.data_dir}"
        )
    calibration_files = [f for f in calibration_dir.iterdir() if Path(f.name).match("sdcalib_*.bin")]
    if not calibration_files:
        raise BadDataFiles(f"Calibration directory {calibration_dir} do not contain sdcalib_*.bin files")

    calibration_file_num_matches = [re.match(r"sdcalib_(\d*).bin", f.name) for f in calibration_files]
    if None in calibration_file_num_matches:
        raise BadDataFiles(f"Calibration epoch number can't be parsed for some sdcalib_*.bin files")
    calibration_file_nums = [int(m.group(1)) for m in calibration_file_num_matches]
    return {num: sdcalib for num, sdcalib in zip(calibration_file_nums, calibration_files)}
