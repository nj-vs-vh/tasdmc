import click
from time import sleep

from tasdmc import config, system, fileio, nodes
from tasdmc.logs import display as display_logs

from ..group import cli
from ..utils import loading_run_by_name, error_catching


@cli.command("progress", help="Display progress for run NAME")
@click.option(
    "-f",
    "--follow",
    is_flag=True,
    default=False,
    help="Update the progress bar every few seconds. Warning: clears terminal!",
)
@click.option(
    "--dump-json", is_flag=True, default=False, help="Dump progress data as json without displaying progress bar"
)
@click.option(
    "--per-node",
    is_flag=True,
    default=False,
    help="Print progress bar independently for each node of the distributed run",
)
@loading_run_by_name
@error_catching
def progress_cmd(follow: bool, dump_json: bool, per_node: bool):
    if config.is_local_run():
        if per_node:
            click.echo("-per-node option ignored for local run")
        if dump_json:
            click.echo(display_logs.PipelineProgress.parse_from_log().dump())
            return
        display_logs.PipelineProgress.parse_from_log().print()
        if follow:
            while True:
                sleep(3)
                click.echo("Updating...")
                plp = display_logs.PipelineProgress.parse_from_log()
                click.clear()
                plp.print()
    else:
        if follow:
            click.echo("--follow option ignored for distributed run")
        plps = nodes.collect_progress_data()
        if per_node:
            for plp in plps:
                plp.print(with_node_name=True)
        else:
            aggregated_plp = None
            for plp in plps:
                if aggregated_plp is None:
                    aggregated_plp = plp
                else:
                    aggregated_plp += plp
            aggregated_plp.print()


@cli.command("status", help="Check status for run NAME")
@click.option("-n", "n_last_messages", default=0, help="Number of messages from worker processes to print")
@click.option("-p", "display_processes", is_flag=True, default=False, help="List worker processes")
@loading_run_by_name
@error_catching
def process_status_cmd(n_last_messages: int, display_processes: bool):
    if config.is_local_run():
        system.print_process_status(fileio.get_saved_main_pid(), display_processes=display_processes)
        if n_last_messages:
            display_logs.print_multiprocessing_log(n_last_messages)
    else:
        nodes.print_statuses(n_last_messages, display_processes)


@cli.command("resources", help="Display system resources utilization for run NAME")
@click.option(
    "--abstime",
    default=False,
    is_flag=True,
    help="Use absolute datetime as X axis; by default Run Evaluation Time is used",
)
@click.option(
    "--latest",
    default=False,
    is_flag=True,
    help="Include only latest run invokation; by default all are merged into one timeline",
)
@click.option(
    "--dump-json",
    default=False,
    is_flag=True,
    help="Dump system resources data as json without displaying plots",
)
@loading_run_by_name
@error_catching
def system_resources_cmd(latest: bool, abstime: bool, dump_json: bool):
    if config.is_local_run():
        srt = display_logs.SystemResourcesTimeline.parse_from_logs(include_previous_runs=(not latest))
        if dump_json:
            click.echo(srt.dump())
        else:
            srt.display(absolute_x_axis=abstime)
    else:
        srts = nodes.collect_system_resources_timelines(latest)
        for srt in srts:
            srt.display(absolute_x_axis=abstime, with_node_name=True)


@cli.command("inputs", help="Display inputs for run NAME")
@loading_run_by_name
@error_catching
def inputs_cmd():
    if config.is_local_run():
        click.echo(fileio.cards_gen_info_log().read_text())
    else:
        nodes.print_inputs()
