from datetime import datetime


DATETIME_FMT = r'%d/%m/%yT%H:%M:%S'


def datetime2str(d: datetime) -> str:
    return d.strftime(DATETIME_FMT)


def str2datetime(s: str) -> datetime:
    return datetime.strptime(s, DATETIME_FMT)
