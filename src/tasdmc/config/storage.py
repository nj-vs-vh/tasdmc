"""A module for storage, loading and dumping configs supplied by user"""

from __future__ import annotations
import yaml
from pathlib import Path
from dataclasses import dataclass, fields, asdict
from abc import ABC, abstractmethod

from typing import Optional, Union, Dict, Any, List, TypeVar, ClassVar
from numbers import Number

from .exceptions import BadConfigError


ConfigContentsType = TypeVar("ConfigContentsType")
StrOrPath = Union[str, Path]


@dataclass
class ConfigContainer:
    contents: ConfigContentsType  # any data structure representing config contents

    _loaded_instance: ClassVar[Optional[ConfigContainer]] = None

    @classmethod
    def loaded(cls) -> ConfigContainer:
        if cls._loaded_instance is None:
            raise RuntimeError(
                f"Attempt to read config before it is loaded, run {cls.__name__}.load('smth.yaml') first."
            )
        return cls._loaded_instance

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded_instance is not None

    @classmethod
    def load(cls, filename: StrOrPath):
        """Used to create singleton instance from file"""
        cls._loaded_instance = cls.load_instance(filename)

    @classmethod
    @abstractmethod
    def load_instance(cls, filename: StrOrPath) -> ConfigContainer:
        pass

    @classmethod
    def dump(cls, filename: Path):
        """Used to dump singleton instance"""
        cls.loaded().dump_instance(filename)

    @abstractmethod
    def dump_instance(self, filename: StrOrPath):
        pass


RunConfigContentsType = Dict[str, Any]


@dataclass
class RunConfig(ConfigContainer):
    contents: RunConfigContentsType = None  # verbatim contents of run.yaml

    @classmethod
    def load_instance(cls, filename: StrOrPath) -> RunConfig:
        contents = _read_yaml(filename)
        if not isinstance(contents, dict):
            raise BadConfigError(f"Run config must contain a mapping, got {contents.__class__.__name__}")
        rc = RunConfig(contents)
        if rc.name is None:
            raise BadConfigError("Run config must include name key!")
        return rc

    def dump_instance(self, filename: StrOrPath):
        _dump_yaml(self.contents, filename)

    def reset_debug_key(self):
        if self.contents is not None:
            self.contents.pop('debug', '')

    @property
    def name(self):
        return self.contents.get("name")


@dataclass
class NodeEntry(ABC):
    host: str
    conda_env: str = None
    name: Optional[str] = None
    config_override: Optional[RunConfigContentsType] = None
    weight: float = 1.0

    def __post_init__(self):
        if self.host != 'self':
            assert self.conda_env is not None, "conda_env key must be specified for all remote nodes!"


@dataclass
class NodesConfig(ConfigContainer):
    contents: List[NodeEntry]  # contents of hosts.yaml's list wrapped in dataclasses

    @classmethod
    def load_instance(cls, filename: StrOrPath) -> NodesConfig:
        raw_contents = _read_yaml(filename)
        if not isinstance(raw_contents, list):
            raise BadConfigError(f"Nodes config must contain a list of items, got {raw_contents.__class__.__name__}")
        node_entries: List[NodeEntry] = []
        field_names = [f.name for f in fields(NodeEntry)]
        for node_entry_data in raw_contents:
            if not isinstance(node_entry_data, dict):
                raise BadConfigError(
                    f"Each node entry in nodes config must be a mapping, got {node_entry_data.__class__.__name__}"
                )
            init_kwargs = {k: v for k, v in node_entry_data.items() if k in field_names}
            node_entries.append(NodeEntry(**init_kwargs))
        all_hosts = [ne.host for ne in node_entries]
        assert len(set(all_hosts)) == len(all_hosts), "Each node must have unique host field"
        return NodesConfig(node_entries)

    @classmethod
    def all_weights(cls) -> List[Number]:
        node_entries: List[NodeEntry] = cls.get()
        return [ne.weight for ne in node_entries]

    def dump_instance(self, filename: StrOrPath):
        raw_contents = [asdict(ne) for ne in self.contents]
        with open(filename, 'w') as f:
            yaml.dump(raw_contents, f)


def _read_yaml(filename: StrOrPath) -> Any:
    try:
        with open(filename, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise BadConfigError(f"Error parsing yaml file: {e}") from e


def _dump_yaml(data: Any, filename: StrOrPath):
    with open(filename, 'w') as f:
        yaml.dump(data, f, sort_keys=False)
