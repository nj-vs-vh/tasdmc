"""Config update functions"""

from __future__ import annotations
from dataclasses import dataclass
import click
import sys

from typing import Any, Optional, List, Dict, Tuple, Generator

from tasdmc import config, fileio
from tasdmc.utils import user_confirmation, items_dot_notation
from .storage import RunConfig


# safe to change means that no work would be lost
SAFE_TO_CHANGE = [
    'description',
    'resources',
    'corsika.default_executable_name',
    'input_files.event_number_multiplier',
    'input_files.subset',
    'spectral_sampling.aux_log10E_min',
    'pipeline.produce_tawiki_dumps',
    'pipeline.archive_all_reconstructed_events'
    'debug',
]


@dataclass
class RunConfigChange:
    key: str  # dot.separated.value
    from_value: Optional[Any]
    to_value: Optional[Any]

    def __str__(self) -> str:
        def value2str(v) -> str:
            return str(v) if v is not None else 'default'

        key_name = f"{('  [safe]' if self.is_safe else '[unsafe]')} {self.key}"
        return (
            click.style(key_name, fg='green' if self.is_safe else 'red')
            + ': '
            + value2str(self.from_value)
            + ' => '
            + value2str(self.to_value)
        )

    @property
    def is_safe(self) -> bool:
        key_parts = self.key.split('.')
        partial_keys = ['.'.join(key_parts[: i + 1]) for i in range(len(key_parts))]
        for partial_key in partial_keys:
            if partial_key in SAFE_TO_CHANGE:
                return True
        else:
            return False

    @staticmethod
    def dict_diff_plain(
        old_dict: Dict, new_dict: Dict
    ) -> Generator[Tuple[str, Tuple[Optional[Any], Optional[Any]]], None, None]:
        # here fqk = fully-qualified key
        old_dict_flat = {fqk: v for fqk, v in items_dot_notation(old_dict)}
        new_dict_flat = {fqk: v for fqk, v in items_dot_notation(new_dict)}

        old_fqk = set(old_dict_flat.keys())
        new_fqk = set(new_dict_flat.keys())

        for fqk in old_fqk - new_fqk:
            yield fqk, (old_dict_flat[fqk], None)

        for fqk in new_fqk - old_fqk:
            yield fqk, (None, new_dict_flat[fqk])

        for fqk in old_fqk.intersection(new_fqk):
            if old_dict_flat[fqk] != new_dict_flat[fqk]:
                yield fqk, (old_dict_flat[fqk], new_dict_flat[fqk])

    @classmethod
    def from_configs(cls, old_config: RunConfig, new_config: RunConfig) -> List[RunConfigChange]:
        return [
            RunConfigChange(key, from_value, to_value)
            for key, (from_value, to_value) in cls.dict_diff_plain(old_config.contents, new_config.contents)
        ]


def update_run_config(new_config_path: str, hard: bool, validate_only: bool):
    new_config = RunConfig.load_instance(new_config_path)
    old_config: RunConfig = RunConfig.loaded()
    if new_config.name != old_config.name:
        click.echo("Attempt to update run's name, aborting")
        sys.exit(1)

    try:
        config_changes = RunConfigChange.from_configs(old_config, new_config)
        if not config_changes:
            click.echo("Nothing to update")
            sys.exit(0)
        click.echo("Following config keys will be updated:")
        for cc in config_changes:
            if cc.key.startswith('before_override'):  # no need to log these, they are just for history
                continue
            click.echo(f"\t{cc}")
    except Exception:
        click.echo("Can't construct config diffs :(")

    RunConfig.load(new_config_path)
    config.validate()
    click.echo("New config seems valid")
    if not validate_only:
        if hard or user_confirmation("Apply?", yes="yes", default=False):
            config.RunConfig.dump(fileio.saved_run_config_file())
            click.echo(f"If the run is active, you will need to abort and continue it for changes to take effect")
        else:
            click.echo("Config changes not applied")
