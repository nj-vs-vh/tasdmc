import warnings
from numbers import Number
from typing import List, TypeVar, Union

from numpy.typing import NDArray

from . import dstreader_core as dstc
from .bank_docs import generated_bank_docs

_SwigGeneratedBankObject = TypeVar("_SwigGeneratedBankObject")

_SwigOpaquePointer = TypeVar("_SwigOpaquePointer")


class Bank:
    """Generic wrapper for bank object, its only job is to dispatch user to custom accessors
    whenever they request an array field. The preferred way to obtain an instance of Bank is
    via DstFile's get_bank method.

    To get a field from bank, use dict-like syntax:
    >>> rusdraw = dst.get_bank("rusdraw")
    >>> fadc = rusdraw["fadc"]
    """

    def __init__(self, name: str, bank_obj: _SwigGeneratedBankObject):
        self.name = name  # name is stored without trailing underscore
        self.bank_obj = bank_obj
        self.bank_class = bank_obj.__class__

    def __str__(self) -> str:
        return f"{self.name} bank, wrapping {self.bank_obj}"

    @property
    def doc(self) -> str:
        try:
            return generated_bank_docs[self.name + "_"]
        except KeyError:
            raise RuntimeError(f"No generated documentation available for {self.name!r} bank")

    @property
    def keys(self) -> List[str]:
        return [
            p
            for p in dir(self.bank_class)
            # thisown property is internal SWIG's stuff
            if p != "thisown" and isinstance(getattr(self.bank_class, p), property)
        ]

    def __getitem__(self, key: str) -> Union[Number, NDArray, _SwigOpaquePointer]:
        value = getattr(self.bank_obj, key, None)
        if value is None:
            raise KeyError(
                f"{self.name} bank does not containt {key} field! Use .keys() method to see available fields"
            )
        if type(value).__name__ == "SwigPyObject":
            # ooops seems like an opaque SWIG object, probably an array, maybe we have a custom accessor for it?
            accessor_func_name = f"get_{self.name}_{key}"
            accessor_func = getattr(dstc, accessor_func_name, None)
            if accessor_func is None:
                warnings.warn(
                    f"Can't interpret value of field {key} in a meaningful way: no default nor "
                    + "custom accessors seem to exist; returning opaque pointer, but you "
                    + "will likely not be able to use it.",
                    RuntimeWarning,
                )
                value: _SwigOpaquePointer
                return value
            else:
                value: NDArray = accessor_func()
                return value
        else:
            value: Number
            return value
