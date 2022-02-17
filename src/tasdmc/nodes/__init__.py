import click
from concurrent.futures import ThreadPoolExecutor
import time

from typing import Callable, Generator, List

from matplotlib.pyplot import title

from tasdmc import config, fileio
from tasdmc.utils import user_confirmation
from tasdmc.logs.display import PipelineProgress, SystemResourcesTimeline
from .node_executor import NodeExecutor, NodeExecutorResult, node_executors_from_config


def _echo_ok():
    click.secho("OK", fg='green')


def _echo_fail():
    click.secho("FAIL", fg='red')


def _run_on_nodes_in_parallel(
    func: Callable[[NodeExecutor], NodeExecutorResult]
) -> Generator[NodeExecutorResult, None, None]:
    node_executors = node_executors_from_config()
    with ThreadPoolExecutor(max_workers=len(node_executors)) as e:
        for res in e.map(func, node_executors):
            yield res


def check_all():
    click.echo("Checking nodes connectivity... ", nl=False)

    def check(ne: NodeExecutor) -> NodeExecutorResult:
        return ne.check()

    failed_results = [r for r in _run_on_nodes_in_parallel(check) if not r.success]

    if failed_results:
        _echo_fail()
        for res in failed_results:
            click.echo(f"{click.style(res.node_exec_name, bold=True)}: {res.msg}")
        raise RuntimeError(f"Nodes check failed")
    else:
        _echo_ok()


def run_all_dry():
    click.echo(f"Checking if nodes are ready to run their parts of the simulation...")
    failed_nodes = []
    for result in _run_on_nodes_in_parallel(lambda ex: ex.run_simulation(dry=True)):
        click.secho(f"{result.node_exec_name}: ", nl=False, bold=True)
        if result.success:
            _echo_ok()
        else:
            _echo_fail()
            click.echo(result.msg)
            failed_nodes.append(result.node_exec_name)
    if failed_nodes:
        raise RuntimeError("Run on following nodes failed: " + ", ".join(failed_nodes))


def run_all():
    click.echo(f"Running...")
    for result in _run_on_nodes_in_parallel(lambda ex: ex.run_simulation(dry=False)):
        if not result.success:
            click.secho(f"Failed to run {result.node_exec_name}: {result.msg}", fg="red")


def continue_all(rerun_step_on_input_hash_mismatch: bool, disable_input_hash_checks: bool):
    cmdline_flags = ""
    if rerun_step_on_input_hash_mismatch:
        cmdline_flags += "--rerun-step-on-input-hash-mismatch "
    if disable_input_hash_checks:
        cmdline_flags += "--disable-input-hash-checks "

    def continue_(ex: NodeExecutor) -> NodeExecutorResult:
        ex.run(f"tasdmc continue {ex.node_run_name} {cmdline_flags}", disown=True)
        time.sleep(1.0)  # waiting before trying to retrieve disowned command log
        res = ex.run(f"cat {ex.DISOWNED_COMMAND_LOG}", with_activation=False)
        if res.return_code == 0:
            msg = NodeExecutorResult.format_stream(res.stdout, title="command log")
        else:
            msg = "\tUnable to retrieve contents of command log"
        return NodeExecutorResult(True, str(ex), msg)

    click.echo(f"Continuing nodes...")
    for result in _run_on_nodes_in_parallel(continue_):
        click.secho(f"{result.node_exec_name}", bold=True)
        click.echo(result.msg)


def abort_all(safe: bool = False):
    safe_opt = "--safe" if safe else ""

    def abort(ex: NodeExecutor) -> NodeExecutorResult:
        return NodeExecutorResult.from_invoke_result(
            ex.run(f"tasdmc abort {ex.node_run_name} --confirm {safe_opt}"), ex
        )

    click.echo(f"Aborting nodes...")
    failed_nodes = []
    for result in _run_on_nodes_in_parallel(abort):
        click.secho(f"\n{result.node_exec_name}", bold=True)
        click.echo(result.msg)
        if not result.success:
            failed_nodes.append(result.node_exec_name)
    if failed_nodes:
        raise RuntimeError("Abort on following nodes failed: " + ", ".join(failed_nodes))


def update_configs(hard: bool, validate_only: bool):
    click.echo(f"Checking node configs...")

    failed_nodes = []
    for result in _run_on_nodes_in_parallel(lambda ex: ex.update_config(dry=True)):
        click.secho(f"\n{result.node_exec_name}", bold=True)
        click.echo(result.msg)
        if not result.success:
            failed_nodes.append(result.node_exec_name)

    if failed_nodes:
        raise RuntimeError("Some nodes refused to update confis: " + ", ".join(failed_nodes))

    if not validate_only and (hard or user_confirmation("Apply?", yes="yes", default=False)):
        click.echo("Applying changes...")
        all_updated_successfully = True
        for result in _run_on_nodes_in_parallel(lambda ex: ex.update_config(dry=False)):
            if not result.success:
                click.echo(f"Failed to apply changes on {result.node_exec_name}", fg="red")
                all_updated_successfully = False
        # this guard is likely redundant since we are performing dry run first, but still, to be safe...
        if all_updated_successfully:
            config.RunConfig.dump(fileio.saved_run_config_file())
            config.NodesConfig.dump(fileio.saved_nodes_config_file())


def collect_progress_data() -> List[PipelineProgress]:
    def collect(ex: NodeExecutor) -> NodeExecutorResult:
        return NodeExecutorResult.from_invoke_result(ex.run(f"tasdmc progress {ex.node_run_name} --dump-json"), ex)

    click.echo(f"Collecting progress data from nodes...")
    plps: List[PipelineProgress] = []
    some_failed = False
    for res in _run_on_nodes_in_parallel(collect):
        click.secho(f"{res.node_exec_name}: ", bold=True, nl=False)
        if res.success:
            _echo_ok()
            plp = PipelineProgress.load(res.data)
            plp.node_name = str(res.node_exec_name)
            plps.append(plp)
        else:
            _echo_fail()
            click.echo(res.msg)
            some_failed = True
    if some_failed:
        click.secho("Error collecting data from some nodes, results are incomplete", fg="red")
    return plps


def print_statuses(n_last_messages: int, display_processes: bool):
    click.echo(f"Checking nodes' statuses...")

    def status(ex: NodeExecutor) -> NodeExecutorResult:
        res = ex.run(
            f"tasdmc status {ex.node_run_name} -n {n_last_messages} {'-p' if display_processes else ''}",
        )
        return NodeExecutorResult.from_invoke_result(res, ex)

    for res in _run_on_nodes_in_parallel(status):
        click.secho(f"\n{res.node_exec_name}", bold=True)
        click.echo(res.msg)


def print_inputs():
    click.echo(f"Printing nodes' inputs...")

    def inputs(ex: NodeExecutor) -> NodeExecutorResult:
        res = ex.run(f"tasdmc inputs {ex.node_run_name}")
        return NodeExecutorResult.from_invoke_result(res, ex)

    for res in _run_on_nodes_in_parallel(inputs):
        click.secho(f"\n{res.node_exec_name}", bold=True)
        click.echo(res.msg)


def collect_system_resources_timelines(latest: bool):
    def collect(ex: NodeExecutor) -> NodeExecutorResult:
        return NodeExecutorResult.from_invoke_result(
            ex.run(f"tasdmc resources {ex.node_run_name} --dump-json {'--latest' if latest else ''}"), ex
        )

    click.echo(f"Collecting system monitoring data from nodes...")
    srts: List[SystemResourcesTimeline] = []
    some_failed = False
    for res in _run_on_nodes_in_parallel(collect):
        click.secho(f"{res.node_exec_name}: ", bold=True, nl=False)
        if res.success:
            _echo_ok()
            srt = SystemResourcesTimeline.load(res.data)
            srt.node_name = res.node_exec_name
            srts.append(srt)
        else:
            _echo_fail()
            click.echo(res.msg)
            some_failed = True
    if some_failed:
        click.secho("Error collecting data from some nodes, results are incomplete", fg="red")
    return srts


def update_tasdmc_on_nodes():
    cmd = (
        "! test -z $TASDMC_SRC_DIR && "
        + "cd $TASDMC_SRC_DIR && "
        + "git pull && "
        + ". scripts/reinstall.sh --no-clear"
    )

    def update_tasdmc(ex: NodeExecutor) -> NodeExecutorResult:
        return NodeExecutorResult.from_invoke_result(ex.run(cmd), ex)

    click.echo(f"Updating tasdmc version on nodes")
    for res in _run_on_nodes_in_parallel(update_tasdmc):
        click.secho(f"\n{res.node_exec_name}: ", bold=True, nl=False)
        if res.success:
            _echo_ok()
        else:
            _echo_fail()
        click.echo(res.msg)
