"""Replacement for deprecated sdmc_run_sdmc_calib_extract from sdanalysis"""

import click
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, Future
from datetime import datetime, date

from typing import List

from tasdmc import config
from tasdmc.utils import batches
from tasdmc.c_routines_wrapper import run_sdmc_calib_extract


DAYS_IN_EPOCH = 30


def _date_from_raw_calibration_file(raw_calib_file: Path) -> date:
    return datetime.strptime(raw_calib_file.name, r'tasdcalib_pass2_%y%m%d.dst').date()


def extract_calibration(raw_calibration_data_dir: Path, n_threads: int = 1):
    if not raw_calibration_data_dir.exists():
        click.echo(f"Raw calibration data directory {raw_calibration_data_dir} not found, aborting")
        return
    constants_file = raw_calibration_data_dir / 'const/tasdconst_pass2.dst'
    if not constants_file.exists():
        click.echo(f"Constants file {constants_file} not found, aborting")
        return

    raw_calibration_files = list((raw_calibration_data_dir / 'calib').iterdir())
    raw_calibration_by_date = {_date_from_raw_calibration_file(rcf): rcf for rcf in raw_calibration_files}
    # calibration always starts on May 11 and ends on May 10
    start_date = min([d for d in raw_calibration_by_date.keys() if d.month == 5 and d.day == 11])
    end_date = max([d for d in raw_calibration_by_date.keys() if d.month == 5 and d.day == 10])
    if end_date < start_date:
        click.echo("Raw calibration files cover less than a year, aborting")
    raw_calibration_files = [rfc for d, rfc in raw_calibration_by_date.items() if start_date <= d <= end_date]

    n_years = end_date.year - start_date.year
    output_files_dir = config.Global.data_dir / f'sdcalib_{n_years}_yrs_from_{start_date.year}_to_{end_date.year}'
    if output_files_dir.exists():
        click.echo(f"Calibration direcotry {output_files_dir} already exists")
        return

    click.echo(f"Extracting calibration for {n_years} years (from {start_date.isoformat()} to {end_date.isoformat()})")
    with ProcessPoolExecutor(max_workers=n_threads) as executor:
        futures: List[Future] = []
        for i_epoch, raw_files_in_epoch in enumerate(batches(raw_calibration_files, size=DAYS_IN_EPOCH)):
            f = executor.submit(
                run_sdmc_calib_extract,
                constants_file=constants_file,
                output_file=output_files_dir / f'sdcalib_{i_epoch}.bin',
                raw_calibration_files=raw_files_in_epoch,
            )
            futures.append(f)
        [f.result() for f in futures]
