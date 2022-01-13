import click
from pathlib import Path
import gdown
from gdown.cached_download import assert_md5sum

from tasdmc import fileio, extract_calibration

from ..group import cli
from ..utils import error_catching


@cli.command(
    "extract-calibration",
    help="Exctract calibration from raw per-day data",
)
@click.option(
    "-r",
    "--raw-data",
    "raw_data_dir",
    required=True,
    type=click.Path(exists=True, resolve_path=True),
    help='Directory containing raw calibration data (calib and const subfolders with .dst files',
)
@click.option(
    "-p",
    "--parallel",
    "parallel_threads",
    type=click.INT,
    default=1,
    help='Number of threads to run in',
)
@error_catching
def extract_calibration_cmd(raw_data_dir: str, parallel_threads: int):
    extract_calibration.extract_calibration(Path(raw_data_dir), parallel_threads)


@cli.command("download-data-files", help="Download data files necessary for the simulation (total of ~350 Mb)")
@error_catching
def download_data_files_cmd():
    for data_file, gdrive_id, expected_md5 in (
        (fileio.DataFiles.sdgeant, '1ZTSrrAg2T8bvIDhPuh2ruVShmubwvTWG', '0cebc42f86e227e2fb2397dd46d7d981'),
        (fileio.DataFiles.atmos, '1qZfUNXAyqVg5HwH9BYUGVQ-UDsTwl4FQ', '254c7999be0a48bd65e4bc8cbea4867f'),
    ):
        if not data_file.exists():
            data_file.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=gdrive_id, output=str(data_file))
        assert_md5sum(data_file, expected_md5)


@cli.command("list", help="List existing runs")
@error_catching
def list_cmd():
    click.echo('\n'.join(fileio.get_all_run_names()))
