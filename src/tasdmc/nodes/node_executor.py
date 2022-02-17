from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from io import StringIO
import click
import copy
from matplotlib.pyplot import title
import yaml
import re
from uuid import uuid4

import invoke
import socket
from fabric import Connection, Result

from typing import TextIO, List, Optional, Dict, Any

from tasdmc import __version__, config
from tasdmc.config.storage import NodeEntry, NodesConfig, RunConfig
from tasdmc.utils import get_dot_notation, set_dot_notation, items_dot_notation


@dataclass
class NodeExecutorResult:
    """Object to return from thread-parallelized code"""

    success: bool
    node_name: str
    msg: Optional[str] = None


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

    def save_run_config_to_node(self) -> Path:
        rc: RunConfig = RunConfig.loaded()
        base_run_config = rc.contents
        node_run_config = copy.deepcopy(base_run_config)

        override = self.node_entry.config_override
        if override is not None:
            for fqk, override_value in items_dot_notation(override):
                base_value = get_dot_notation(base_run_config, fqk, default=None)
                if base_value == override_value:
                    continue
                set_dot_notation(node_run_config, fqk, override_value)
                if base_value is not None:  # saving original values under dedicated key
                    set_dot_notation(node_run_config, "before_override." + fqk, base_value)

        set_dot_notation(node_run_config, "input_files.subset.all_weights", NodesConfig.all_weights())
        set_dot_notation(node_run_config, "input_files.subset.this_idx", self.index)
        node_run_config["name"] = self.node_run_name
        node_run_config["parent_distributed_run"] = {
            "name": config.run_name(),
            "host": socket.gethostname(),
        }

        return self.save_to_node(StringIO(yaml.dump(node_run_config, sort_keys=False)))

    def remove_from_node(self, file: Path):
        self.run(f"rm {file}", with_activation=False)

    def run_simulation(self, dry: bool = False):
        node_run_config_path = self.save_run_config_to_node()
        dry_opt = '--dry' if dry else ''
        self.run(f"tasdmc run-local -r {node_run_config_path} --remove-run-config-file {dry_opt}", disown=(not dry))

    def update_config(self, dry: bool = False) -> bool:
        new_node_run_config = self.save_run_config_to_node()
        try:
            opt = "--validate-only" if dry else "--hard"
            res = self.run(
                f"tasdmc update-config {self.node_run_name} -r {new_node_run_config} {opt}",
                check_result=(not dry),
                echo_streams=(dry),
            )
            return res is not None and res.return_code == 0
        finally:
            self.remove_from_node(new_node_run_config)

    @abstractmethod
    def check(self) -> NodeExecutorResult:
        pass

    @property
    @abstractmethod
    def node_run_name(self) -> str:
        pass

    @property
    @abstractmethod
    def activation_cmd(self) -> Optional[str]:
        pass

    @abstractmethod
    def save_to_node(self, contents: TextIO) -> Path:
        """Returns path to file on the node"""
        pass

    def run(
        self, cmd: str, with_activation: bool = True, check_result: bool = True, echo_streams: bool = False, **kwargs
    ) -> Optional[Result]:
        for fabric_param_name, default_value in [
            ('hide', 'both'),
            ('warn', True),
            ('pty', False),
        ]:
            if fabric_param_name not in kwargs:
                kwargs[fabric_param_name] = default_value
        if with_activation:
            if self.activation_cmd is not None:
                cmd = f"{self.activation_cmd} && {cmd}"
        if kwargs.get('disown') == True:
            cmd = cmd + " &> /tmp/tasdmc-disowned.log"
        res = self._run(cmd, **kwargs)
        if check_result:
            self._check_command_result(res)
        if echo_streams:
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            if stdout:
                click.echo(_format_stream(stdout, title="stdout"))
            if stderr and stderr != stdout:
                click.echo(_format_stream(res.stdout, title="stderr", is_err=True))
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
            for stream_contents in [
                _format_stream(res.stdout, title='stdout'),
                _format_stream(res.stderr, title='stderr', is_err=True),
            ]:
                if stream_contents:
                    errmsg += f'\n{stream_contents}\n'
            raise RuntimeError(errmsg)


@dataclass
class RemoteNodeExecutor(NodeExecutor):
    connection: Connection

    def __del__(self):
        self.connection.close()

    def check(self) -> NodeExecutorResult:
        try:
            with self.connection:
                res: Result = self.run("tasdmc --version", pty=False)
                remote_node_version_match = re.match(r"tasdmc, version (?P<version>.*)", str(res.stdout))
                assert remote_node_version_match is not None, f"Can't parse tasdmc version from output '{res.stdout}'"
                remote_node_version = remote_node_version_match.groupdict()['version']
                assert (
                    remote_node_version == __version__
                ), f"Mismatching version '{remote_node_version}', expected '{__version__}'"
            return NodeExecutorResult(success=True, node_name=self.node_entry.name)
        except Exception as e:
            return NodeExecutorResult(success=False, node_name=self.node_entry.name, msg=str(e))

    @property
    def node_run_name(self) -> str:
        return f"{config.run_name()}:node-from-{socket.gethostname()}"

    @property
    def activation_cmd(self) -> str:
        return f"conda activate {self.node_entry.conda_env}"

    def save_to_node(self, contents: TextIO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-remote-node-artifact-{uuid4().hex[:8]}')
        self.connection.put(contents, str(remote_tmp))
        return remote_tmp

    def _run(self, cmd: str, **kwargs) -> Optional[Result]:
        return self.connection.run(cmd, **kwargs)


class LocalNodeExecutor(NodeExecutor):
    def check(self) -> bool:
        return NodeExecutorResult(success=True, node_name=self.node_entry.name)

    @property
    def node_run_name(self) -> str:
        return f"{config.run_name()}:node-local"

    @property
    def activation_cmd(self):
        return None

    def save_to_node(self, contents: TextIO) -> Path:
        remote_tmp = Path(f'/tmp/tasdmc-self-node-artifact-{uuid4().hex[:8]}')
        with open(remote_tmp, "w") as f:
            f.write(contents.read())
        return remote_tmp

    def _run(self, cmd: str, **kwargs) -> Optional[Result]:
        # print(f"\n\n{cmd}\n\n")
        return invoke.run(cmd, **kwargs)


def node_executors_from_config() -> List[NodeExecutor]:
    executors = []
    for i, ne in enumerate(_node_entries_from_config()):
        if ne.host == 'self':
            executors.append(LocalNodeExecutor(node_entry=ne, index=i))
        else:
            executors.append(RemoteNodeExecutor(node_entry=ne, index=i, connection=Connection(host=ne.host)))
    return executors


def _node_entries_from_config() -> List[NodeEntry]:
    return NodesConfig.loaded().contents


def _format_stream(stream: str, is_err: bool = False, title: Optional[str] = None) -> str:
    stream = stream.replace("tput: No value for $TERM and no -T specified", "")  # annoying terminal error
    stream = stream.strip()
    color = "red" if is_err else "blue"
    formatted = '\n'.join([click.style('\t| ', fg=color) + line for line in stream.splitlines()])
    if title is not None:
        formatted = "\t" + click.style(title, bold=True, fg=color) + "\n" + formatted
    return formatted
