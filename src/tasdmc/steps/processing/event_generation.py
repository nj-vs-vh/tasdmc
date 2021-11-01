"""Throwing CORSIKA-generated showers onto an SD grid, taking calibration into account"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from functools import lru_cache
import random

from typing import List, Dict, Iterable, Tuple

from tasdmc import fileio, config
from tasdmc.steps.base import Files, FileInFileOutPipelineStep
from tasdmc.steps.exceptions import FilesCheckFailed, BadDataFiles
from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, check_dst_file_not_empty, passed
from .corsika2geant import C2GOutputFiles, Corsika2GeantStep
from .tothrow_generation import TothrowFile, TothrowGenerationStep

from tasdmc.c_routines_wrapper import (
    test_sdmc_spctr_runnable,
    run_sdmc_spctr,
    set_limits_for_sdmc_spctr,
    run_sdmc_tsort,
    concatenate_dst_files,
    list_events_in_dst_file,
)


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
    merged_events_file: Path
    stdout: Path
    stderr: Path
    dst_file_by_epoch: Dict[int, Path]
    calibration_file_by_epoch: Dict[int, Path]

    @property
    def must_exist(self) -> List[Path]:
        return [self.stdout, self.stderr, self.merged_events_file]

    @classmethod
    def from_input(cls, input_files: C2GOutputWithTothrowFiles) -> EventFiles:
        corsika_event_name = input_files.c2g_output.corsika_event_name
        calibration_by_epoch = _get_calibration_files_by_epoch()
        max_epoch_len = len(str(max(calibration_by_epoch.keys())))
        dst_file_by_epoch = {}
        for epoch in calibration_by_epoch.keys():
            epoch_str = format(epoch, f"0{max_epoch_len}d")
            dst_file_by_epoch[epoch] = fileio.events_dir() / f'{corsika_event_name}_epoch{epoch_str}.dst.gz'
        return EventFiles(
            merged_events_file=fileio.events_dir() / f'{corsika_event_name}.dst.gz',
            stdout=fileio.events_dir() / f'{corsika_event_name}.events.stdout',
            stderr=fileio.events_dir() / f'{corsika_event_name}.events.stderr',
            dst_file_by_epoch=dst_file_by_epoch,
            calibration_file_by_epoch=calibration_by_epoch,
        )

    def prepare_for_step_run(self):
        self.stderr.unlink(missing_ok=True)  # it may not be created in _run but left from previous runs

    def iterate_epochs_files(self) -> Iterable[Tuple[int, Path, Path]]:
        return (
            (epoch, self.dst_file_by_epoch[epoch], self.calibration_file_by_epoch[epoch])
            for epoch in sorted(self.calibration_file_by_epoch.keys())
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=[" $$$ dst_get_block_ : End of input file reached"])
        check_last_line_contains(self.stdout, "OK")
        check_dst_file_not_empty(self.merged_events_file)


class EventsGenerationStep(FileInFileOutPipelineStep):
    input_: C2GOutputWithTothrowFiles
    output: EventFiles

    @property
    def description(self) -> str:
        return f"Throwing CORSIKA events on SD grid for {self.input_.c2g_output.corsika_event_name}"

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

        stdout = self.output.stdout.open('w')  # not using 'with open(...)' to save indentation level :)
        stderr = self.output.stderr.open('w')
        stdout.write(f"Poissonian mean N particles: {n_particles_per_epoch}\n")

        # generating event file for each epoch
        events_thrown_by_file = dict()
        for epoch, epoch_events_file, sdcalib_file in self.output.iterate_epochs_files():
            epoch_log_file = Path(str(epoch_events_file) + '.log')
            if epoch_log_file.exists() and epoch_events_file.exists() and check_dst_file_not_empty(epoch_events_file):
                stdout.write(f'Events for epoch {epoch} ({sdcalib_file.name}) were already generated\n')
            else:
                stdout.write(f'Generating events for epoch {epoch} ({sdcalib_file.name})\n')
                epoch_log_file.unlink(missing_ok=True)
                for i_try in range(1, n_try + 1):
                    stdout.write(f'\tAttempt {i_try}/{n_try}\n')
                    # fmt: off
                    sdmc_spctr_exited_ok = run_sdmc_spctr(
                        self.input_.c2g_output.tile, epoch_events_file, n_particles_per_epoch,
                        random.randint(1, int(1e6)), epoch, sdcalib_file, smear_energies, epoch_log_file, epoch_log_file,
                        # TODO: azi.txt file may be passed here
                    )
                    # fmt: on
                    if sdmc_spctr_exited_ok and passed(check_last_line_contains)(epoch_log_file, must_contain="Done"):
                        break
                else:
                    stderr.write(f'Events for epoch {epoch} not generated after {n_try} attempts\n')
                    epoch_events_file.unlink(missing_ok=True)
                    continue

            # counting how many events were actually thrown in the succesfull sdmc_spctr call
            # NOTE: the distribution of N events thrown may not be actually Poisson due to many attempts made;
            #       if, for example, attempts with larger N fail, the distribution will be skewed to the left from
            #       the mean. this needs further investigation...
            events_thrown_match = re.findall(r"^Number of Events Thrown: (\d*)$", epoch_log_file.read_text(), re.M)
            if not events_thrown_match:
                stderr.write(
                    f'Events generated ({epoch_events_file}) but log does not contain a number of events thrown\n'
                )
                epoch_events_file.unlink(missing_ok=True)
                continue
            events_thrown_from_log = int(events_thrown_match[-1])
            events_thrown_from_dst = len(list_events_in_dst_file(epoch_events_file))
            if events_thrown_from_log != events_thrown_from_dst:
                stderr.write(f'N events thrown according to log differs from N events in {epoch_events_file}\n')
                epoch_events_file.unlink(missing_ok=True)
                continue
            events_thrown = events_thrown_from_dst

            stdout.write(f'\tEvents actually generated: {events_thrown}\n')
            events_thrown_by_file[epoch_events_file] = events_thrown

            # if >0 events thrown, sort them by time
            if events_thrown > 0:
                # epoch_events_file_sorted_temp = Path(str(epoch_events_file) + '.timesorted')
                epoch_events_file_stem = epoch_events_file.name.split('.')[0]
                epoch_events_file_unsorted = epoch_events_file.parent / (
                    epoch_events_file_stem + '_unsorted.dst.gz'
                )
                epoch_events_file.rename(epoch_events_file_unsorted)
                if run_sdmc_tsort(epoch_events_file_unsorted, epoch_events_file, epoch_log_file, epoch_log_file):
                    epoch_events_file_unsorted.unlink()
                else:
                    stderr.write(
                        f'Time-sorting of events in {epoch_events_file.name} failed, see details in {epoch_log_file}\n'
                    )
                    epoch_events_file_unsorted.unlink(missing_ok=True)
                    epoch_events_file.unlink(missing_ok=True)
                    continue

        # if events for all epochs were generated, merge them into one final file
        if not all(epoch_events_file.exists() for _, epoch_events_file, _ in self.output.iterate_epochs_files()):
            stderr.write('Some epoch events were not generated\n')
        else:
            epoch_event_files_to_merge = [
                epoch_events_file
                for _, epoch_events_file, _ in self.output.iterate_epochs_files()
                if events_thrown_by_file[epoch_events_file] > 0
            ]
            concatenate_log = Path(str(self.output.merged_events_file) + '.log')
            concatenate_dst_files(
                epoch_event_files_to_merge, self.output.merged_events_file, concatenate_log, concatenate_log
            )
            for _, epoch_events_file, _ in self.output.iterate_epochs_files():
                epoch_events_file.unlink()
            stdout.write("\nOK\n")

        stdout.close()
        stderr.close()

        # TEMP: sometimes this step partially fails for no obvious reason;
        #       here we explicitly throw an error and send the detailed report to failed pipelines
        #       hence it will be accessible even after continued runs in logs/before-YYYY-MM-DDThh:mm:ss
        stderr_text = self.output.stderr.read_text().strip()
        if stderr_text:
            raise FilesCheckFailed(f"Step partially failed:\n{stderr_text}")

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
        raise BadDataFiles("Calibration epoch number can't be parsed for some sdcalib_*.bin files")
    calibration_file_nums = [int(m.group(1)) for m in calibration_file_num_matches]
    return {num: sdcalib for num, sdcalib in zip(calibration_file_nums, calibration_files)}
