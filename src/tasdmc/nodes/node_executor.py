from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from io import StringIO
import click
import copy
import yaml
import re

import invoke
import socket
from fabric import Connection, Result

from typing import TextIO, List, Optional, Dict, Any

from tasdmc import __version__, config
from tasdmc.config.storage import NodeEntry, NodesConfig, RunConfig
from tasdmc.utils import get_dot_notation, set_dot_notation, items_dot_notation


@dataclass
class NodeExecutor(ABC):
    node_entry: NodeEntry
    index: int

    def __str__(self) -> str:
        return (
            f"{self.node_entry.name} ({self.node_entry.host})"
            if self.node_entry.name is not None
            else self.node_entry.host
        )

    def run_simulation(self, dry: bool = False):
        base_run_config = RunConfig.get()
        node_run_config = copy.deepcopy(base_run_config)

        override = self.node_entry.config_override
        if override is not None:
            for fqk, override_value in items_dot_notation(override):
                base_value = get_dot_notation(base_run_config, fqk)
                if base_value == override_value:
                    continue
                set_dot_notation(node_run_config, fqk, override_value)
                # saving original values under dedicated key
                set_dot_notation(node_run_config, "before_override." + fqk, base_value)

        set_dot_notation(node_run_config, "input_files.subset.all_weights", NodesConfig.all_weights())
        set_dot_notation(node_run_config, "input_files.subset.this_idx", self.index)
        node_run_config["name"] = self.node_run_name

        node_run_config_path = self.save_to_node(StringIO(yaml.dump(node_run_config, sort_keys=False)))
        try:
            tasdmc_cmd = 'run-local' if not dry else 'run-local-dry'
            self.run(f"tasdmc {tasdmc_cmd} -r {node_run_config_path}", disown=(not dry and self.allows_disown))
        finally:
            self.run(f"rm {node_run_config_path}", with_activation=False)

    def continue_simulation(self):
        self.run(f"tasdmc continue {self.node_run_name}", disown=self.allows_disown)

    @abstractmethod
    def check(self) -> bool:
        pass

    @property
    @abstractmethod
    def node_run_name(self) -> str:
        pass

    @property
    @abstractmethod
    def activation_cmd(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def allows_disown(self) -> bool:
        pass

    @abstractmethod
    def save_to_node(self, contents: TextIO) -> Path:
        """Returns path to file on the node"""
        pass

    def run(self, cmd: str, with_activation: bool = True, **kwargs) -> Optional[Result]:
        for fabric_param_name, default_value in [('hide', 'both'), ('warn', True), ('pty', True)]:
            if fabric_param_name not in kwargs:
                kwargs[fabric_param_name] = default_value
        if with_activation:
            if self.activation_cmd is not None:
                cmd = f"{self.activation_cmd} && {cmd}"
        res = self._run(cmd, **kwargs)
        self._check_command_result(res)
        return res

    @abstractmethod
    def _run(self, cmd: str, **kwargs) -> Optional[Result]:
        """Run shell command on the node"""
        pass

    def _check_command_result(self, res: Optional[Result]):
        if res is None:
            return
        if res.return_code != 0:
            errmsg = f"Command on node {self} exited with error (code {res.return_code})"
            for stream_contents, stream_name in [
                (_postprocess_stream(res.stdout), 'stdout'),
                (_postprocess_stream(res.stderr), 'stderr'),
            ]:
                if stream_contents:
                    errmsg += f'\n\tCaptured {stream_name}:\n{stream_contents}'
            raise RuntimeError(errmsg)


@dataclass
class RemoteNodeExecutor(NodeExecutor):
    connection: Connection

    def check(self) -> bool:
        try:
            with self.connection:
                res: Result = self.run("tasdmc --version")
                remote_node_version_match = re.match(r"tasdmc, version (?P<version>.*)", str(res.stdout))
                assert remote_node_version_match is not None, f"Can't parse tasdmc version from output '{res.stdout}'"
                remote_node_version = remote_node_version_match.groupdict()['version']
                assert (
                    remote_node_version == __version__
                ), f"Mismatching version '{remote_node_version}', expected '{__version__}'"
            return True
        except Exception as e:
            click.echo(f"{self}: {e}")
            return False

    @property
    def node_run_name(self) -> str:
        return f"{config.run_name()}:node-from-{socket.gethostname()}"

    @property
    def activation_cmd(self) -> str:
        return f"conda activate {self.node_entry.conda_env}"

    @property
    def allows_disown(self) -> bool:
        return False  # for some reason remote nodes do not run after disown

    def save_to_node(self, contents: TextIO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-node-artifact-{abs(hash(self.connection))}')
        self.connection.put(contents, str(remote_tmp))
        return remote_tmp

    def _run(self, cmd: str, **kwargs) -> Optional[Result]:
        return self.connection.run(cmd, **kwargs)


class LocalNodeExecutor(NodeExecutor):
    def check(self) -> bool:
        return True

    @property
    def node_run_name(self) -> str:
        return f"{config.run_name()}:node-local"

    @property
    def activation_cmd(self):
        return None

    @property
    def allows_disown(self) -> bool:
        return True

    def save_to_node(self, contents: TextIO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-self-node-artifact')
        with open(remote_tmp, "w") as f:
            f.write(contents.read())
        return remote_tmp

    def _run(self, cmd: str, **kwargs) -> Optional[Result]:
        # print(f"\n\n{cmd}\n\n")
        return invoke.run(cmd, **kwargs)


@lru_cache(1)
def node_executors_from_config() -> List[NodeExecutor]:
    executors = []
    for i, ne in enumerate(_node_entries_from_config()):
        if ne.host == 'self':
            executors.append(LocalNodeExecutor(node_entry=ne, index=i))
        else:
            executors.append(RemoteNodeExecutor(node_entry=ne, index=i, connection=Connection(host=ne.host)))
    return executors


def _node_entries_from_config() -> List[NodeEntry]:
    node_entries: List[NodeEntry] = NodesConfig.get()
    return node_entries


def _postprocess_stream(stream: str) -> str:
    stream = stream.replace("tput: No value for $TERM and no -T specified", "")  # annoying terminal error
    stream = stream.strip()
    stream = '\n'.join(['\t| ' + line for line in stream.splitlines()])
    return stream
