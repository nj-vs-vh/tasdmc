import click

from tasdmc import fileio, inspect, hard_cleanup

from ..group import cli
from ..options import run_config_option, nodes_config_option
from ..utils import run_standard_pipeline_in_background, loading_run_by_name, error_catching


@cli.command("fix-failed", help="Fix failed pipelines")
@click.option("--hard", is_flag=True, default=False, help="If specified, removes all failed pipeline files entirely")
@loading_run_by_name
@error_catching
def fix_failed_pipelines_cmd(hard: bool):
    failed_pipeline_ids = fileio.get_failed_pipeline_ids()
    if not failed_pipeline_ids:
        click.echo("No failed pipelines to fix")
        return
    if hard:
        hard_cleanup.delete_all_pipelines(failed_pipeline_ids)
    else:
        inspect.inspect_and_fix_failed(failed_pipeline_ids)


@cli.command("inspect", help="Inspect pipelines step-by-step")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Print verbose information about steps")
@click.option("-p", "--page", "pagesize", default=0, help="Page size or 0 for no pagination (default)")
@click.option("-f", "--failed", is_flag=True, default=False, help="Inspect only failed pipelines")
@loading_run_by_name
@error_catching
def inspect_cmd(pagesize: int, verbose: bool, failed: bool):
    pipeline_ids = fileio.get_failed_pipeline_ids() if failed else fileio.get_all_pipeline_ids()
    inspect.inspect_pipelines(pipeline_ids, page_size=pagesize, verbose=verbose, fix=False)
