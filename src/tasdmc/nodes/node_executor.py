from abc import ABC, abstractmethod
from dataclasses import dataclass
import invoke
from fabric import Connection, Result
from pathlib import Path
from functools import lru_cache
import click
import copy
import re

from typing import IO, Any, List

from tasdmc import __version__
from tasdmc.config.storage import NodeEntry, NodesConfig, RunConfig, RunConfigContentsType
from tasdmc.utils import get_dot_notation, set_dot_notation, items_dot_notation


@dataclass
class NodeExecutor(ABC):
    node_entry: NodeEntry

    def __str__(self) -> str:
        return (
            f"{self.node_entry.name} ({self.node_entry.host})"
            if self.node_entry.name is not None
            else self.node_entry.host
        )

    def get_remote_run_config(self) -> RunConfigContentsType:
        base = RunConfig.get()
        override = self.node_entry.config_override
        if override is None:
            return base
        patched = copy.deepcopy(base)
        for fqk, override_value in items_dot_notation(override):
            base_value = get_dot_notation(base, fqk)
            if base_value == override_value:
                continue
            set_dot_notation(patched, fqk, override_value)
            # saving original values under dedicated key
            set_dot_notation(patched, "before_override." + fqk, base_value)
        return patched

    @abstractmethod
    def check(self) -> bool:
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

    def check(self) -> bool:
        try:
            with self.connection:
                remote_check_cmd = f"conda activate {self.node_entry.conda_env} && tasdmc --version"
                res: Result = self.connection.run(remote_check_cmd, hide='both', warn=True)
                if res.return_code != 0:
                    errmsg = f"Remote node command error (exit code {res.return_code})"
                    for stream_contents, stream_name in [
                        (_postprocess_stream(res.stdout), 'stdout'),
                        (_postprocess_stream(res.stderr), 'stderr'),
                    ]:
                        if stream_contents:
                            errmsg += f'\n\tCaptured {stream_name}:\n{stream_contents}'
                    raise Exception(errmsg)
                remote_node_version_match = re.match(r"tasdmc, version (?P<version>.*)", str(res.stdout))
                assert remote_node_version_match is not None, f"Can't parse tasdmc version from output '{res.stdout}'"
                remote_node_version = remote_node_version_match.groupdict()['version']
                assert (
                    remote_node_version == __version__
                ), f"Mismatching version {remote_node_version}, expected {__version__}"
            return True
        except Exception as e:
            click.echo(f"{self}: {e}")
            return False

    def save_to_node(self, contents: IO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-node-artifact-{abs(hash(self.connection))}')
        self.connection.put(contents, remote_tmp)
        return remote_tmp

    def run(self, cmd: str, *args, **kwargs) -> Result:
        return self.connection.run(cmd, *args, **kwargs)


class LocalNodeExecutor(NodeExecutor):
    def check(self) -> bool:
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


def _postprocess_stream(stream: str) -> str:
    stream = stream.replace("tput: No value for $TERM and no -T specified", "")  # annoying terminal error
    stream = stream.strip()
    stream = '\n'.join(['\t> ' + line for line in stream.splitlines()])
    return stream
