import click

from tasdmc import fileio, inspect, hard_cleanup, config

from ..group import cli
from ..utils import loading_run_by_name, error_catching


@cli.command("fix-failed", help="Fix failed pipelines for RUN_NAME")
@click.option("--hard", is_flag=True, default=False, help="If specified, removes all failed pipeline files entirely")
@loading_run_by_name
@error_catching
def fix_failed_pipelines_cmd(hard: bool):
    if config.is_distributed_run():
        click.echo("Not available for distributed run, please fix your nodes manually")
        return
    failed_pipeline_ids = fileio.get_failed_pipeline_ids()
    if not failed_pipeline_ids:
        click.echo("No failed pipelines to fix")
        return
    if hard:
        hard_cleanup.delete_all_pipelines(failed_pipeline_ids)
    else:
        inspect.inspect_and_fix_failed(failed_pipeline_ids)


@cli.command("inspect", help="Step-by-step inspection of pipelines in RUN_NAME")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Print verbose information about steps")
@click.option("-p", "--page", "pagesize", default=0, help="Page size; 0 for no pagination (default)")
@click.option("-f", "--failed", is_flag=True, default=False, help="Inspect only failed pipelines")
@loading_run_by_name
@error_catching
def inspect_cmd(pagesize: int, verbose: bool, failed: bool):
    if config.is_distributed_run():
        click.echo("Not available for distributed run, please inspect your nodes manually")
        return
    pipeline_ids = fileio.get_failed_pipeline_ids() if failed else fileio.get_all_pipeline_ids()
    inspect.inspect_pipelines(pipeline_ids, page_size=pagesize, verbose=verbose, fix=False)
