from datetime import datetime, timedelta


DATETIME_FMT = r'%d/%m/%yT%H:%M:%S'


def datetime2str(d: datetime) -> str:
    return d.strftime(DATETIME_FMT)


def str2datetime(s: str) -> datetime:
    return datetime.strptime(s, DATETIME_FMT)


def timedelta2str(t: timedelta) -> str:
    hours = t.seconds // (3600)
    minutes = t.seconds // (60) - hours * 60
    if t.days:
        hours -= t.days * 24
        return f"{t.days}d {hours}h {minutes}m"
    else:
        return f"{hours}h {minutes}m"
