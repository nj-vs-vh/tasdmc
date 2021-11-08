from pathlib import Path


def pipeline_id_from_failed_file(pipeline_failed_file: Path) -> str:
    return pipeline_failed_file.name.replace('.failed', '')
