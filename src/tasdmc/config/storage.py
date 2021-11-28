"""A module for storage, loading and dumping configs supplied by user"""

import yaml
from pathlib import Path
from dataclasses import dataclass, fields, asdict
from abc import ABC, abstractmethod

from typing import Optional, Union, Dict, Any, List, TypeVar

from .exceptions import ConfigNotReadError, BadConfigError


ConfigContentsType = TypeVar("ConfigContentsType")


class ConfigContainer:
    contents: Optional[ConfigContentsType] = None  # any data structure representing config contents

    @classmethod
    def get(cls) -> ConfigContentsType:
        if cls.contents is None:
            raise ConfigNotReadError(
                f"Attempt to read config before it is loaded, run config.{cls.__name__}.load('smth.yaml') first."
            )
        return cls.contents

    @classmethod
    def is_loaded(cls) -> bool:
        return cls.contents is not None

    @classmethod
    @abstractmethod
    def load(cls, filename: Union[str, Path]):
        pass

    @classmethod
    @abstractmethod
    def dump(cls, filename: Path):
        pass



RunConfigContentsType = Dict[str, Any]



class RunConfig(ConfigContainer):
    contents: Optional[RunConfigContentsType] = None  # verbatim contents of run.yaml

    @classmethod
    def load(cls, filename: Union[str, Path]):
        raw_contents = _read_yaml(filename)
        if not isinstance(raw_contents, dict):
            raise BadConfigError(f"Run config must contain a mapping, got {raw_contents.__class__.__name__}")
        cls.contents = raw_contents

    @classmethod
    def dump(cls, filename: Path):
        _dump_yaml(cls.get(), filename)

    @classmethod
    def reset_debug_key(cls):
        if cls.contents is not None:
            cls.contents.pop('debug', '')


@dataclass
class NodeEntry(ABC):
    host: str
    user: str = None
    conda_env: str = None
    name: Optional[str] = None
    config_override: Optional[RunConfigContentsType] = None
    weight: float = 1.0

    def __post_init__(self):
        if self.host != 'self':
            assert self.conda_env is not None, "conda_env key must be specified for all remote nodes!"


class NodesConfig(ConfigContainer):
    contents: Optional[List[NodeEntry]] = None  # contents of hosts.yaml wrapped in dataclasses

    @classmethod
    def load(cls, filename: Union[str, Path]):
        raw_contents = _read_yaml(filename)
        if not isinstance(raw_contents, list):
            raise BadConfigError(f"Nodes config must contain a list of items, got {raw_contents.__class__.__name__}")
        cls.contents = []
        field_names = [f.name for f in fields(NodeEntry)]
        for node_entry_data in raw_contents:
            if not isinstance(node_entry_data, dict):
                raise BadConfigError(
                    f"Each node entry in nodes config must be a mapping, got {node_entry_data.__class__.__name__}"
                )
            init_kwargs = {k: v for k, v in node_entry_data.items() if k in field_names}
            cls.contents.append(NodeEntry(**init_kwargs))
        all_hosts = [ne.host for ne in cls.contents]
        assert len(set(all_hosts)) == len(all_hosts), "Each node must have unique host field"

    @classmethod
    def dump(cls, filename: Path):
        raw_contents = [asdict(ne) for ne in cls.contents]
        with open(filename, 'w') as f:
            yaml.dump(raw_contents, f)


def _read_yaml(filename: Union[str, Path]) -> Any:
    try:
        with open(filename, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise BadConfigError(f"Error parsing yaml file: {e}") from e


def _dump_yaml(data: Any, filename: Path):
    with open(filename, 'w') as f:
        yaml.dump(data, f, sort_keys=False)
