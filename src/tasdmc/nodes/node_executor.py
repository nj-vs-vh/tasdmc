from abc import ABC, abstractmethod
from dataclasses import dataclass
import invoke
from fabric import Connection, Result
from pathlib import Path
from functools import lru_cache

from typing import IO, Any, List

from tasdmc.config.storage import NodeEntry, NodesConfig


@dataclass
class NodeExecutor(ABC):
    node_entry: NodeEntry

    def __str__(self) -> str:
        return self.node_entry.host

    @abstractmethod
    def check_connectivity(self) -> bool:
        pass

    @abstractmethod
    def save_to_node(self, contents: IO) -> Path:
        """Returns path to file on the node"""
        pass

    @abstractmethod
    def run(self, cmd: str, *args, **kwargs) -> Any:
        """Run shell command on the node"""
        pass


@dataclass
class RemoteNodeExecutor(NodeExecutor):
    connection: Connection

    def check_connectivity(self) -> bool:
        with self.connection:
            try:
                self.connection.run('uname', hide='both')
                return True
            except Exception:
                return False

    def save_to_node(self, contents: IO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-node-artifact-{abs(hash(self.connection))}')
        self.connection.put(contents, remote_tmp)
        return remote_tmp

    def run(self, cmd: str, *args, **kwargs) -> Result:
        return self.connection.run(cmd, *args, **kwargs)


class LocalNodeExecutor(NodeExecutor):

    def check_connectivity(self) -> bool:
        return True

    def save_to_node(self, contents: IO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-self-node-artifact')
        with open(remote_tmp, contents.mode) as f:
            f.write(contents.read())

    def run(self, cmd: str, *args, **kwargs) -> Result:
        return invoke.run(cmd, *args, **kwargs)


@lru_cache(1)
def node_executors_from_config() -> List[NodeExecutor]:
    executors = []
    for ne in _node_entries_from_config():
        if ne.host == 'self':
            executors.append(LocalNodeExecutor(node_entry=ne))
        else:
            executors.append(RemoteNodeExecutor(node_entry=ne, connection=Connection(host=ne.host, user=ne.user)))
    return executors


def _node_entries_from_config() -> List[NodeEntry]:
    node_entries: List[NodeEntry] = NodesConfig.get()
    return node_entries
