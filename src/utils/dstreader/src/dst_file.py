from pathlib import Path
from typing import Generator, List, Union

from . import dstreader_core as dstc
from .units import get_unit_id, free_unit_id
from .bank import Bank


class DstFile:
    def __init__(self, filename: Union[str, Path]):
        if isinstance(filename, Path):
            filename = str(filename.resolve())
        self.filename = filename

    def open(self):
        self.is_open = True
        self.unit = get_unit_id()
        dstc.dstOpenUnit(self.unit, self.filename, dstc.MODE_READ_DST)

    def close(self):
        dstc.dstCloseUnit(self.unit)
        free_unit_id(self.unit)
        self.is_open = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc_args):
        self.close()

    def get_bank(self, bank_name: str) -> Bank:
        if not self.event_is_read:
            raise ValueError("Banks are only available when iterating over events")
        bank_obj_name = bank_name + '_'  # naming convention of global structs in C code
        bank_obj = getattr(dstc, bank_obj_name, None)
        if bank_obj is None:
            raise KeyError("No such bank!")
        else:
            return Bank(bank_name, bank_obj)

    def events(self) -> Generator[List[str], None, None]:
        """Generator function yielding event numbers"""
        if not self.is_open:
            raise ValueError("DstFile must be open to iterate over events")
        n_banks = dstc.n_banks_total_()
        want = dstc.newBankList(n_banks)
        got = dstc.newBankList(n_banks)
        event_ptr = dstc.new_intp()  # int pointer
        while True:
            rc = dstc.eventRead(self.unit, want, got, event_ptr)
            self.event_is_read = True
            if rc < 0:
                self.event_is_read = False
                break

            # same as dstlist.run - iterating over banks in the event and yielding their names
            bank_names: List[str] = []
            i_ptr = dstc.new_intp()
            dstc.intp_assign(i_ptr, 0)
            while True:
                bank_id = dstc.itrBankList(got, i_ptr)
                if bank_id == 0:
                    break
                # 1024 is a max len of copied bank name - playing it safe
                _, bank_name = dstc.eventNameFromId(bank_id, 1024)
                bank_names.append(bank_name)
            dstc.delete_intp(i_ptr)

            yield bank_names

        dstc.delete_intp(event_ptr)