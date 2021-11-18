"""Throwing CORSIKA-generated showers onto an SD grid, taking calibration into account"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import os
import re
import random
import tarfile
import resource
from gdown.cached_download import assert_md5sum

from typing import List, Dict, Iterable, Tuple

from tasdmc import fileio, config
from tasdmc.steps.base import Files, PipelineStep
from tasdmc.steps.exceptions import FilesCheckFailed, BadDataFiles
from tasdmc.steps.utils import check_file_is_empty, check_last_line_contains, check_dst_file_not_empty, passed
from .corsika2geant import C2GOutputFiles, Corsika2GeantStep
from .tothrow_generation import TothrowFile, TothrowGenerationStep

from tasdmc.c_routines_wrapper import (
    concatenate_dst_files,
    list_events_in_dst_file,
)

from tasdmc.c_routines_wrapper import execute_routine, Pipes


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
    concat_log: Path
    logs_archive: Path
    events_file_by_epoch: Dict[int, Path]
    events_log_by_epoch: Dict[int, Path]

    calibration_file_by_epoch: Dict[int, Path]

    @property
    def id_paths(self) -> List[Path]:
        return [self.merged_events_file, self.stdout, self.stderr]

    @property
    def must_exist(self) -> List[Path]:
        return self.id_paths

    @property
    def all_files(self) -> List[Path]:
        return self.id_paths + [
            *self.events_file_by_epoch.values(),
            *self.events_log_by_epoch.values(),
            self.concat_log,
        ]

    @classmethod
    def from_input(cls, input_files: C2GOutputWithTothrowFiles) -> EventFiles:
        corsika_event_name = input_files.c2g_output.corsika_event_name
        calibration_by_epoch = _get_calibration_files_by_epoch()
        max_epoch_len = len(str(max(calibration_by_epoch.keys())))
        events_file_by_epoch: Dict[int, Path] = {}
        events_log_by_epoch = {}
        for epoch in calibration_by_epoch.keys():
            epoch_str = format(epoch, f"0{max_epoch_len}d")
            events_file_by_epoch[epoch] = fileio.events_dir() / f'{corsika_event_name}_epoch{epoch_str}.dst.gz'
        events_log_by_epoch = {k: Path(str(v) + '.log') for k, v in events_file_by_epoch.items()}
        return EventFiles(
            merged_events_file=fileio.events_dir() / f'{corsika_event_name}.dst.gz',
            stdout=fileio.events_dir() / f'{corsika_event_name}.evgen.stdout',
            stderr=fileio.events_dir() / f'{corsika_event_name}.evgen.stderr',
            concat_log=fileio.events_dir() / f'{corsika_event_name}.dstconcat.stderr',
            logs_archive=fileio.events_dir() / f'{corsika_event_name}.per-epoch-logs.tar.gz',
            events_file_by_epoch=events_file_by_epoch,
            events_log_by_epoch=events_log_by_epoch,
            calibration_file_by_epoch=calibration_by_epoch,
        )

    def prepare_for_step_run(self):
        self.stderr.unlink(missing_ok=True)  # it may not be created in _run but left from previous runs

    def per_epoch_files(self) -> Iterable[Tuple[int, Path, Path, Path]]:
        """epoch number, events file, log file, calibration file"""
        return (
            (
                epoch,
                self.events_file_by_epoch[epoch],
                self.events_log_by_epoch[epoch],
                self.calibration_file_by_epoch[epoch],
            )
            for epoch in sorted(self.calibration_file_by_epoch.keys())
        )

    def _check_contents(self):
        check_file_is_empty(self.stderr, ignore_strings=["$$$ dst_get_block_ : End of input file reached"])
        check_last_line_contains(self.stdout, "OK")
        check_dst_file_not_empty(self.merged_events_file)


class EventsGenerationStep(PipelineStep):
    input_: C2GOutputWithTothrowFiles
    output: EventFiles

    @property
    def description(self) -> str:
        return f"Throwing CORSIKA shower {self.input_.c2g_output.corsika_event_name} on SD grid to produce MC events"

    @classmethod
    def from_corsika2geant_with_tothrow(
        cls, c2g_step: Corsika2GeantStep, tothrow_step: TothrowGenerationStep
    ) -> EventsGenerationStep:
        input_ = C2GOutputWithTothrowFiles(c2g_step.output, tothrow_step.output)
        return EventsGenerationStep(
            input_=input_, output=EventFiles.from_input(input_), previous_steps=[tothrow_step, c2g_step]
        )

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
        for epoch, epoch_events_file, epoch_log_file, sdcalib_file in self.output.per_epoch_files():
            if epoch_log_file.exists() and epoch_events_file.exists() and check_dst_file_not_empty(epoch_events_file):
                stdout.write(f'Events for epoch {epoch} ({sdcalib_file.name}) were already generated\n')
            else:
                stdout.write(f'Generating events for epoch {epoch} ({sdcalib_file.name})\n')
                epoch_log_file.unlink(missing_ok=True)
                for i_try in range(1, n_try + 1):
                    stdout.write(f'\tAttempt {i_try}/{n_try}\n')
                    with Pipes(epoch_log_file, epoch_log_file, append=True) as (stdout, stderr):
                        sdmc_spctr_res = execute_routine(
                            _get_sdmc_spctr_executable(),
                            [
                                self.input_.c2g_output.tile,
                                epoch_events_file,
                                n_particles_per_epoch,
                                random.randint(1, int(1e6)),
                                epoch,
                                sdcalib_file,
                                fileio.DataFiles.atmos,
                                1 if smear_energies else 0,
                                # TODO: azi.txt file may optionally be passed here
                            ],
                            stdout=stdout,
                            stderr=stderr,
                            global_=True,
                            check_errors=False,
                        )
                    if sdmc_spctr_res.returncode == 0 and passed(check_last_line_contains)(epoch_log_file, "Done"):
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
                epoch_events_file_unsorted = epoch_events_file.parent / (epoch_events_file_stem + '_unsorted.dst.gz')
                epoch_events_file.rename(epoch_events_file_unsorted)
                with Pipes(epoch_log_file, epoch_log_file, append=True) as (stdout, stderr):
                    tsort_res = execute_routine(
                        'sdmc_tsort.run',
                        [epoch_events_file_unsorted, '-o1f', epoch_events_file],
                        stdout,
                        stderr,
                        global_=True,
                        check_errors=False,
                    )
                epoch_events_file_unsorted.unlink(missing_ok=True)
                if tsort_res.returncode != 0:
                    stderr.write(
                        f'Time-sorting of events in {epoch_events_file.name} failed, see details in {epoch_log_file}\n'
                    )
                    epoch_events_file.unlink(missing_ok=True)

        # if events for all epochs were generated, merge them into one final file
        if not all(epoch_events_file.exists() for _, epoch_events_file, *_ in self.output.per_epoch_files()):
            stderr.write('Some epoch events were not generated\n')
        else:
            epoch_event_files_to_merge = [
                epoch_events_file
                for _, epoch_events_file, *_ in self.output.per_epoch_files()
                if events_thrown_by_file[epoch_events_file] > 0
            ]
            concatenate_dst_files(
                epoch_event_files_to_merge,
                self.output.merged_events_file,
                self.output.concat_log,
                self.output.concat_log,
            )
            with tarfile.open(self.output.logs_archive, 'w:gz') as tar:
                for _, epoch_events_file, epoch_log, _ in self.output.per_epoch_files():
                    epoch_events_file.unlink()
                    tar.add(epoch_log, epoch_log.name, recursive=False)
                    epoch_log.unlink()
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
        assert (
            fileio.DataFiles.atmos.exists()
        ), f"{fileio.DataFiles.atmos} file not found, use 'tasdmc download-data-files'"
        assert_md5sum(fileio.DataFiles.atmos, '254c7999be0a48bd65e4bc8cbea4867f', quiet=True)
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


@lru_cache(1)
def _get_sdmc_spctr_executable():
    """Find sdmc_spctr executable as it may be compiled with different suffixes"""
    sdmc_spctr_candidates: List[Path] = []
    PATH = os.environ['PATH']
    for executables_dir in set(PATH.split(':')):
        executables_dir = executables_dir.strip()
        if not executables_dir:
            continue
        executables_dir = Path(executables_dir)
        if not executables_dir.exists():
            continue
        for executable_file in executables_dir.iterdir():
            if executable_file.name.startswith('sdmc_spctr'):
                sdmc_spctr_candidates.append(executable_file)

    if not sdmc_spctr_candidates:
        raise FileNotFoundError("sdmc_spctr_*.run not found on $PATH!")
    elif len(sdmc_spctr_candidates) > 1:
        requested_sdmc_spctr_name = config.get_key("throwing.sdmc_spctr_executable_name", default=None)
        if requested_sdmc_spctr_name is None:
            raise FileNotFoundError(
                "Multiple sdmc_spctr_*.run executables found on $PATH!:\n"
                + '\n'.join([f"\t{exe}" for exe in sdmc_spctr_candidates])
                + "\nSpecify throwing.sdmc_spctr_executable_name in run config"
            )
        else:
            sdmc_spctr_candidates = [ef for ef in sdmc_spctr_candidates if ef.name == requested_sdmc_spctr_name]
            if not sdmc_spctr_candidates:
                raise FileNotFoundError(f"Requested {requested_sdmc_spctr_name} executable not found on $PATH")
            elif len(sdmc_spctr_candidates) > 1:
                raise FileNotFoundError(
                    f"Found multiple executables matching requested {requested_sdmc_spctr_name}:\n"
                    + '\n'.join([f"\t{exe}" for exe in sdmc_spctr_candidates])
                    + '\nRemove some of them from $PATH to eliminate conflict'
                )
    return sdmc_spctr_candidates[0]  # we've ensured that this is the only option left!


def set_limits_for_sdmc_spctr():
    """Equivalent to ulimit -s unlimited on command line"""
    _, hard_stack_limit = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, hard_stack_limit))


def test_sdmc_spctr_runnable():
    sdmc_spctr = _get_sdmc_spctr_executable()
    res = execute_routine(sdmc_spctr, [], global_=True, check_errors=False)
    if 'Usage: ' not in res.stderr.decode('utf-8'):
        raise OSError(f'{sdmc_spctr} do not work as expected!')
