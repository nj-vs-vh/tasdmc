from datetime import datetime, timedelta


DATETIME_FMT = r'%d/%m/%yT%H:%M:%S'


def datetime2str(d: datetime) -> str:
    return d.strftime(DATETIME_FMT)


def str2datetime(s: str) -> datetime:
    return datetime.strptime(s, DATETIME_FMT)


def timedelta2str(t: timedelta) -> str:
    total_seconds = t.total_seconds()
    total_hours = total_seconds // 3600
    minutes = (total_seconds // 60) - total_hours * 60
    if t.days:
        total_hours -= t.days * 24
        return f"{t.days}d {total_hours}h {minutes}m"
    else:
        return f"{total_hours}h {minutes}m"
