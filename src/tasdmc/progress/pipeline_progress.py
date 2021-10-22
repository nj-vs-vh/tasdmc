from tasdmc import fileio


def mark_failed(pipeline_id: str, errmsg: str):
    fileio.pipeline_failed_file(pipeline_id).touch()  # this is atomic
    with open(fileio.pipeline_failed_file(pipeline_id), 'a') as f:
        f.write('\n' + errmsg + '\n')


def is_failed(pipeline_id: str) -> bool:
    return fileio.pipeline_failed_file(pipeline_id).exists()
