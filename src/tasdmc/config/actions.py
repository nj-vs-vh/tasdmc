"""Config updates are tricky: some fields may be changed safely while others may be not.
This module contains heuristics about how a user can update their config."""

from __future__ import annotations
from dataclasses import dataclass
import yaml
from dictdiffer import diff
import click
import sys

from typing import Any, Optional, List, Dict, Tuple

from tasdmc import config, fileio
from tasdmc.utils import user_confirmation
from .internal import get_config


# safe to change means that no work would be lost
SAFE_TO_CHANGE = ['resources', 'corsika.default_executable_name', 'input_files.event_number_multiplier', 'debug']


@dataclass
class ConfigChange:
    key: str  # dot.separated.value
    from_value: Optional[Any]
    to_value: Optional[Any]

    def __str__(self) -> str:
        return (
            click.style(self.key, fg='green' if self.is_safe else 'red')
            + ': '
            + (str(self.from_value) if self.from_value is not None else 'default')
            + ' => '
            + (str(self.to_value) if self.to_value is not None else 'default')
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
    def unroll(parent_key: str, added_key: str, added_value: Any) -> List[Tuple[str, Any]]:
        """
        Unrolling nested addition/deletions to flat list:

        >>> 'parent_key', 'new_key', {'nested_1': 1, 'nested_2': 2, 'nested_3': {'deep1': 'hello', 'deep2': 'world'}}
                ↓
        >>> ('parent_key.new_key.nested_1', 1)
        >>> ('parent_key.new_key.nested_2', 2)
        >>> ('parent_key.new_key.nested_3.deep1', 'hello')
        >>> ('parent_key.new_key.nested_3.deep2', 'world')
        """
        full_added_key = parent_key + '.' + added_key if parent_key else added_key
        if isinstance(added_value, dict):
            unrolled = []
            for added_subkey, added_subvalue in added_value.items():
                unrolled.extend(ConfigChange.unroll(full_added_key, added_subkey, added_subvalue))
            return unrolled
        else:
            return [(full_added_key, added_value)]

    @classmethod
    def from_diff(cls, old_config: Dict, new_config: Dict) -> List[ConfigChange]:
        changes = []
        for diff_type, changed_key, what_changed in diff(old_config, new_config):
            if diff_type == 'change':
                changes.append(ConfigChange(changed_key, from_value=what_changed[0], to_value=what_changed[1]))
            else:
                unrolled_diffs = []
                for added_key, added_value in what_changed:
                    unrolled_diffs.extend(cls.unroll(changed_key, added_key, added_value))
                for key, value in unrolled_diffs:
                    changes.append(
                        ConfigChange(
                            key,
                            from_value=value if diff_type == 'remove' else None,
                            to_value=value if diff_type == 'add' else None,
                        )
                    )
        return changes


def update_config(new_config_path: str):
    with open(new_config_path, 'r') as f:
        new_config = yaml.safe_load(f)
    config_changes = ConfigChange.from_diff(old_config=get_config(), new_config=new_config)
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

    if 'name' in [cc.key for cc in config_changes]:
        click.echo("Attempt to update run's name, aborting")
        return

    config.load(new_config_path)
    try:
        config.validate()
    except config.BadConfigValue as e:
        click.echo(str(e))
        return
    if user_confirmation("New config seems valid, apply?", yes="yes", default=False):
        config.dump(fileio.saved_run_config_file())
        click.echo(f"You will need to abort-continue run {config.run_name()} for changes to take effect")


def view_config():
    click.echo(f"Run config for '{config.run_name()}':\n")
    yaml.dump(get_config(), sys.stdout, indent=4, sort_keys=False)
