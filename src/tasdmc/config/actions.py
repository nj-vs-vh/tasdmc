"""Config updates are tricky: some fields may be changed safely while others may be not.
This module contains heuristics about how a user can update their config."""

from __future__ import annotations
from dataclasses import dataclass
import yaml
from dictdiffer import diff
import click
import sys

from typing import Any, Optional, List, Dict, Tuple, Literal, cast, Generator

from tasdmc import config, fileio
from tasdmc.utils import user_confirmation
from .internal import get_config


# safe to change means that no work would be lost
SAFE_TO_CHANGE = [
    'resources',
    'corsika.default_executable_name',
    'input_files.event_number_multiplier',
    'debug',
    'spectral_sampling.aux_log10E_min',
]


@dataclass
class ConfigChange:
    key: str  # dot.separated.value
    from_value: Optional[Any]
    to_value: Optional[Any]

    def __str__(self) -> str:
        def value2str(v) -> str:
            return str(v) if v is not None else 'default'

        return (
            click.style(self.key, fg='green' if self.is_safe else 'red')
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
        """Wrapper around dictdiffer.diff func with post-processing:

        1. Unrolling dict-typed additions/deletions to flat lists:
        >>> 'parent_key', 'new_key', {'nested_1': 1, 'nested_2': 2, 'nested_3': {'deep1': 'hello', 'deep2': 'world'}}
                ↓
        >>> ('parent_key.new_key.nested_1', 1)
        >>> ('parent_key.new_key.nested_2', 2)
        >>> ('parent_key.new_key.nested_3.deep1', 'hello')
        >>> ('parent_key.new_key.nested_3.deep2', 'world')

        2. Avoiding in-list recursion

        Returns generator over tuples ("full.changed.key", ["value_from", "value_to"])
        """

        def _get_value(d: Dict, keys: List[str]):
            try:
                value = d
                for key in keys:
                    value = value[key]
                return value
            except KeyError:
                raise RuntimeError(f"Got sequence of keys ({keys}) not found in the dict")

        def _unroll_addel_dicts(parent_key: str, addel_key: str, addel_value: Any):
            full_added_key = parent_key + '.' + addel_key if parent_key else addel_key
            if isinstance(addel_value, dict):
                unrolled = []
                for added_subkey, added_subvalue in addel_value.items():
                    unrolled.extend(_unroll_addel_dicts(full_added_key, added_subkey, added_subvalue))
                return unrolled
            else:
                return [(full_added_key, addel_value)]

        seen_keys = []  # needed because post-processing can generate duplicates
        for diff_type, key, changes in diff(old_dict, new_dict):
            print(f"{diff_type = }, {key = }, {changes = }")

            diff_type = cast(Literal['change', 'remove', 'add'], diff_type)
            if isinstance(key, list):
                key_levels = [k for k in key if isinstance(k, str)]  # dropping in-list indices
                key = '.'.join(key_levels)
            elif isinstance(key, str):
                key_levels = key.split('.')
            else:
                raise RuntimeError(
                    f"Got unexpected changed key from diff function: {key} (type {key.__class__.__name__})"
                )
            if key in seen_keys:
                continue
            seen_keys.append(key)

            try:
                # sometimes we consider 'change' things that dictdiffer considers 'add' or 'remove'
                old_value = _get_value(old_dict, key_levels)
                new_value = _get_value(new_dict, key_levels)
                if isinstance(old_value, list) and isinstance(new_value, list):
                    diff_type = 'change'
            except Exception:
                pass

            if diff_type == 'change':
                yield key, (_get_value(old_dict, key_levels), _get_value(new_dict, key_levels))
            else:
                for addel_key, addel_value in changes:
                    for full_addel_key, simple_addel_value in _unroll_addel_dicts(key, addel_key, addel_value):
                        if diff_type == 'add':
                            change_tuple = (None, simple_addel_value)
                        elif diff_type == 'remove':
                            change_tuple = (simple_addel_value, None)
                        else:
                            raise RuntimeError(f"Got unexpected diff type from diff function: {diff_type}")
                        yield full_addel_key, change_tuple

    @classmethod
    def from_configs(cls, old_config: Dict, new_config: Dict) -> List[ConfigChange]:
        return [
            ConfigChange(key, from_value, to_value)
            for key, (from_value, to_value) in cls.dict_diff_plain(old_config, new_config)
        ]


def update_config(new_config_path: str, hard: bool):
    with open(new_config_path, 'r') as f:
        new_config = yaml.safe_load(f)
    old_config = get_config()
    if new_config['name'] != old_config['name']:
        click.echo("Attempt to update run's name, aborting")
        return
    
    if not hard:
        try:
            config_changes = ConfigChange.from_configs(old_config, new_config)
        except Exception:
            click.echo("Can't parse config diffs. If you are sure you want to proceed, pass --hard flag.")
        if not config_changes:
            click.echo("Nothing to update")
            return
        click.echo(
            "Following config keys will be updated (marked whether is is "
            + f"{click.style('safe', fg='green')} or {click.style('unsafe', fg='red')} "
            + "to change between aborting-continuing run):"
        )
        for cc in config_changes:
            click.echo(f"\t{cc}")

    config.load(new_config_path)
    try:
        config.validate()
    except config.BadConfigValue as e:
        click.echo(str(e))
        return
    if hard or user_confirmation("New config seems valid, apply?", yes="yes", default=False):
        config.dump(fileio.saved_run_config_file())
        click.echo(f"You will need to abort-continue run {config.run_name()} for changes to take effect")
    else:
        click.echo("Aborted")


def view_config():
    click.echo(f"Run config for '{config.run_name()}':\n")
    yaml.dump(get_config(), sys.stdout, indent=4, sort_keys=False)
