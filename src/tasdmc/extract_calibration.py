"""Replacement for deprecated sdmc_run_sdmc_calib_extract from sdanalysis"""

import click
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, Future, as_completed
from tqdm import tqdm
from datetime import datetime, date
from math import ceil

from typing import List

from tasdmc import config
from tasdmc.utils import batches
from tasdmc.c_routines_wrapper import execute_routine, Pipes


DAYS_IN_EPOCH = 30


def _date_from_raw_calibration_file(raw_calib_file: Path) -> date:
    return datetime.strptime(raw_calib_file.name, r'tasdcalib_pass2_%y%m%d.dst').date()


def _run_sdmc_calib_extract(
    constants_file: Path, output_file: Path, raw_calibration_files: List[Path], stdout_file: Path, stderr_file: Path
):
    """Exctracting calibration from a set of per-day raw .dst files and packing it into single epoch calibration"""
    with Pipes(stdout_file, stderr_file) as (stdout, stderr):
        execute_routine(
            'sdmc_calib_extract.run',
            ['-c', constants_file, '-o', output_file, *raw_calibration_files],
            stdout,
            stderr,
            global_=True,
        )


def extract_calibration(raw_calibration_data_dir: Path, n_threads: int = 1):
    if not raw_calibration_data_dir.exists():
        click.echo(f"Raw calibration data directory {raw_calibration_data_dir} not found, aborting")
        return
    raw_calibration_data_dir = raw_calibration_data_dir.resolve()
    constants_file = raw_calibration_data_dir / 'const/tasdconst_pass2.dst'
    if not constants_file.exists():
        click.echo(f"Constants file {constants_file} not found, aborting")
        return
    raw_calibration_files_dir = raw_calibration_data_dir / 'calib'
    if not constants_file.exists():
        click.echo(f"Raw calibration data dir {raw_calibration_files_dir} not found, aborting")
        return
    all_raw_calibration_files = list(raw_calibration_files_dir.iterdir())
    if not all_raw_calibration_files:
        click.echo(f"Raw calibration data dir {raw_calibration_files_dir} is empty, aborting")
        return

    all_raw_calibration_files_by_date = {_date_from_raw_calibration_file(rcf): rcf for rcf in all_raw_calibration_files}
    # calibration always starts on May 11 and ends on May 10
    start_date = min([d for d in all_raw_calibration_files_by_date.keys() if d.month == 5 and d.day == 11])
    end_date = max([d for d in all_raw_calibration_files_by_date.keys() if d.month == 5 and d.day == 10])
    if end_date < start_date:
        click.echo("Raw calibration files cover less than a year, aborting")
        return
    selected_raw_calibration_files_with_date = [
        (d, rfc) for d, rfc in all_raw_calibration_files_by_date.items() if start_date <= d <= end_date
    ]
    selected_raw_calibration_files_with_date.sort(key=lambda d_rfc: d_rfc[0])
    selected_raw_calibration_files = [rfc for _, rfc in selected_raw_calibration_files_with_date]

    n_years = end_date.year - start_date.year
    output_files_dir = config.Global.data_dir / f'sdcalib_{n_years}_yrs_from_{start_date.year}_to_{end_date.year}'
    if output_files_dir.exists():
        click.echo(f"Calibration directory {output_files_dir} already exists")
        return
    output_files_dir.mkdir()

    click.echo(f"Extracting calibration for {n_years} years (from {start_date.isoformat()} to {end_date.isoformat()})")
    with ProcessPoolExecutor(max_workers=n_threads) as executor:
        futures: List[Future] = []
        for i_epoch, raw_files_in_epoch in enumerate(batches(selected_raw_calibration_files, size=DAYS_IN_EPOCH)):
            i_epoch_str = str(i_epoch + 1).rjust(ceil(len(selected_raw_calibration_files) / DAYS_IN_EPOCH), '0')
            f = executor.submit(
                _run_sdmc_calib_extract,
                constants_file=constants_file,
                output_file=output_files_dir / f'sdcalib_{i_epoch_str}.bin',
                stdout_file=output_files_dir / f'{i_epoch_str}.stdout.log',
                stderr_file=output_files_dir / f'{i_epoch_str}.stderr.log',
                raw_calibration_files=raw_files_in_epoch,
            )
            futures.append(f)
        for _ in tqdm(as_completed(futures), total=len(futures)):
            pass
    for file in output_files_dir.iterdir():
        if file.name.endswith('.stdout.log') or file.name.endswith('.stderr.log'):
            file.unlink()
