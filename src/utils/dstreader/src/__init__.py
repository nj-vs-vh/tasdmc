from typing import Generator, Any, List, Union
from pathlib import Path

from . import dstreader_core as core


FREE_UNIT_IDS = set(range(1, core.MAX_DST_FILE_UNITS + 1))


def get_unit_id() -> int:
    if len(FREE_UNIT_IDS) == 0:
        raise Exception("Too many open .dst files!")
    return FREE_UNIT_IDS.pop()


def free_unit_id(unit: int):
    FREE_UNIT_IDS.add(unit)


class DstFile:
    def __init__(self, filename: Union[str, Path]):
        if isinstance(filename, Path):
            filename = str(filename.resolve())
        self.filename = filename

    def open(self):
        self.is_open = True
        self.unit = get_unit_id()
        core.dstOpenUnit(self.unit, self.filename, core.MODE_READ_DST)

    def close(self):
        core.dstCloseUnit(self.unit)
        free_unit_id(self.unit)
        self.is_open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc_args):
        self.close()

    def get_bank(self, bank_name: str) -> Any:
        if not self.event_read:
            raise ValueError("get_bank function is only available when iterating over events")
        bank_obj = getattr(core, bank_name)
        if bank_obj is None:
            raise KeyError("No such bank!")
        else:
            return bank_obj

    def events(self) -> Generator[List[str], None, None]:
        """Generator function yielding event numbers """
        if not self.is_open:
            raise ValueError("DstFile must be used as a context manager to iterate events")
        n_banks = core.n_banks_total_()
        want = core.newBankList(n_banks)
        got = core.newBankList(n_banks)
        event_ptr = core.new_intp()  # int pointer
        while True:
            rc = core.eventRead(self.unit, want, got, event_ptr)
            self.event_read = True
            if rc < 0:
                self.event_read = False
                break

            # same as dstlist.run - iterating over banks in the event and yielding their names
            bank_names: List[str] = []
            i_ptr = core.new_intp()
            core.intp_assign(i_ptr, 0)
            while True:
                bank_id = core.itrBankList(got, i_ptr)
                if bank_id == 0:
                    break
                # 1024 is a max len of copied bank name - playing it safe
                _, bank_name = core.eventNameFromId(bank_id, 1024)
                bank_names.append(bank_name)
            core.delete_intp(i_ptr)

            yield bank_names

        core.delete_intp(event_ptr)


