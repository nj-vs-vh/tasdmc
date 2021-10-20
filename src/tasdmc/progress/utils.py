from datetime import datetime


def datetime2str(d: datetime) -> str:
    return d.strftime(r'%d/%m/%y %H:%M:%S')
