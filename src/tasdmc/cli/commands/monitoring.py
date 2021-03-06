import click
from time import sleep

from tasdmc import config, fileio, nodes
from tasdmc.system import processes
from tasdmc.logs import display as display_logs

from ..group import cli
from ..utils import loading_run_by_name, error_catching


@cli.command("info", help="Display general info for RUN_NAME")
@loading_run_by_name
@error_catching
def info_cmd():
    click.secho("Run: ", dim=True, nl=False)
    click.secho(config.run_name(), bold=True)
    click.secho("Description: ", dim=True, nl=False)
    click.echo(str(config.get_key("description", default="(none)")))
    section_delimiter = "\n" + "=" * 30 + "\n"
    if config.is_local_run():
        click.echo("Local", nl=False)
        parent_dict = config.get_key("parent_distributed_run", default=None)
        if parent_dict is None:
            click.echo()
        else:
            click.echo(
                f", spawned by distributed run {click.style(parent_dict['name'], bold=True)} "
                + f"running on {click.style(parent_dict['host'], bold=True)}"
            )
    else:
        click.echo(section_delimiter)
        click.echo(f"Distributed across {len(config.NodesConfig.loaded().contents)} nodes:\n")
        config.NodesConfig.dump(stdout=True)
    click.echo(section_delimiter)
    click.echo("Run config:\n")
    config.RunConfig.dump(stdout=True)


@cli.command("progress", help="Display progress for RUN_NAME")
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
@click.option(
    "--ansi-colors",
    is_flag=True,
    default=False,
    help="Disable full RGB print and use only default ANSI colors; useful for some terminals",
)
@loading_run_by_name
@error_catching
def progress_cmd(follow: bool, dump_json: bool, per_node: bool, ansi_colors: bool):
    full_color = not ansi_colors
    if config.is_local_run():
        if per_node:
            click.echo("-per-node option ignored for local run")
        if dump_json:
            click.echo(display_logs.PipelineProgress.parse_from_log().dump())
            return
        display_logs.PipelineProgress.parse_from_log().print(full_color=full_color)
        if follow:
            while True:
                sleep(3)
                click.echo("Updating...")
                plp = display_logs.PipelineProgress.parse_from_log()
                click.clear()
                plp.print(full_color=full_color)
    else:
        if follow:
            click.echo("--follow option ignored for distributed run")
        if dump_json:
            click.echo("--dump-json option ignored for distributed run")
        plps = nodes.collect_progress_data()
        if per_node:
            for plp in plps:
                click.echo()
                plp.print(with_node_name=True, full_color=full_color)
        else:
            aggregated_plp = None
            for plp in plps:
                if aggregated_plp is None:
                    aggregated_plp = plp
                else:
                    aggregated_plp += plp
            aggregated_plp.print(full_color=full_color)


@cli.command("status", help="Check status for run RUN_NAME")
@click.option("-n", "n_last_messages", default=0, help="Number of messages from worker processes to print")
@click.option("-p", "display_processes", is_flag=True, default=False, help="List worker processes")
@loading_run_by_name
@error_catching
def process_status_cmd(n_last_messages: int, display_processes: bool):
    if config.is_local_run():
        saved_main_pid = fileio.get_saved_main_pid()
        if saved_main_pid is None:
            click.echo("Run was never launched (probably just forked?)")
        else:
            processes.print_run_processes_status(
                main_pid=fileio.get_saved_main_pid(), display_processes=display_processes
            )
        if n_last_messages:
            display_logs.print_multiprocessing_log(n_last_messages)
    else:
        nodes.print_statuses(n_last_messages, display_processes)


@cli.command("resources", help="Display system resources utilization for RUN_NAME")
@click.option(
    "--abstime",
    default=False,
    is_flag=True,
    help="Use absolute datetime as X axis; by default run time is used",
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
@click.option(
    "--per-node",
    default=False,
    is_flag=True,
    help="Display resource plots independently for each node of the distributed run",
)
@loading_run_by_name
@error_catching
def system_resources_cmd(latest: bool, abstime: bool, dump_json: bool, per_node: bool):
    if config.is_local_run():
        timeline = display_logs.SystemResourcesTimeline.parse_from_logs(include_previous_runs=(not latest))
        if dump_json:
            click.echo(timeline.dump())
        else:
            timeline.display(absolute_x_axis=abstime)
    else:
        if dump_json:
            click.echo("--dump-json option ignored for distributed run")
        timelines = nodes.collect_system_resources_timelines(latest)
        if per_node:
            for timeline in timelines:
                print()
                timeline.display(absolute_x_axis=abstime, with_node_name=True)
        else:
            display_logs.SystemResourcesTimeline.display_multiple(timelines)


@cli.command("inputs", help="Display inputs for RUN_NAME")
@loading_run_by_name
@error_catching
def inputs_cmd():
    if config.is_local_run():
        click.echo(fileio.cards_gen_info_log().read_text())
    else:
        nodes.print_inputs()
