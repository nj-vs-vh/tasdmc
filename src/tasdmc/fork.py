from pathlib import Path
import shutil
import click

from tasdmc import fileio, config
from tasdmc.steps import ParticleFileSplittingStep
from tasdmc.steps.base.files import Files, NotAllRetainedFiles, OptionalFiles
from tasdmc.pipeline import get_steps
from tasdmc.steps.corsika_cards_generation import generate_corsika_cards


def symlink_if_exists(link: Path, src: Path):
    if src.exists() and not link.exists():
        click.echo(f"\t{link.relative_to(config.Global.runs_dir)} -> {src.relative_to(config.Global.runs_dir)}")
        link.symlink_to(src)


def fork_run(fork_name: str, after: str):
    if after == 'corsika':
        break_at_step_class = ParticleFileSplittingStep
    else:
        raise ValueError("Currently forking only after 'corsika' is possible")

    src_run_dir = fileio.run_dir()

    def in_src_run_dir(p: Path) -> Path:
        return src_run_dir / p.relative_to(fileio.run_dir())

    config.RunConfig.loaded().update_name(fork_name)
    fileio.prepare_run_dir()
    assert (
        fileio.run_dir() != src_run_dir
    ), "Something's wrong with the fork! LRU caches in fileio module are probably not cleared"
    # we're forked!

    # copying all the input hash files, for that they must be generated with new relative path - based names
    click.echo("Copying input file hashes to the forked run to allow seamless continuation")
    for input_hash_file in in_src_run_dir(fileio.input_hashes_dir()).iterdir():
        shutil.copy(input_hash_file, fileio.input_hashes_dir() / input_hash_file.name)
    cards = generate_corsika_cards(logging=False)
    # with non-batched steps list we can stop as soon we see a single step after the fork point
    steps = get_steps(cards, batched=False)
    for step in steps:
        if isinstance(step, break_at_step_class):
            break
        click.echo(f"Symlinking files for step {step}")
        for files in (step.input_, step.output):
            for link in files.all_files:
                src = in_src_run_dir(link)
                symlink_if_exists(link, src)
                if isinstance(files, NotAllRetainedFiles):
                    src = files._with_deleted_suffix(src)
                    link = files._with_deleted_suffix(link)
                    symlink_if_exists(link, src)
