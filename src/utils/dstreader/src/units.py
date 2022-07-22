from . import dstreader_core as dstc

FREE_UNIT_IDS = set(range(1, dstc.MAX_DST_FILE_UNITS + 1))


def get_unit_id() -> int:
    if len(FREE_UNIT_IDS) == 0:
        raise Exception("Too many open .dst files!")
    return FREE_UNIT_IDS.pop()


def free_unit_id(unit: int):
    FREE_UNIT_IDS.add(unit)
