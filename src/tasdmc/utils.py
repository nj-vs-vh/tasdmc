from typing import TypeVar, Sequence


SequenceValue = TypeVar('SequenceValue')


def batches(seq: Sequence[SequenceValue], size: int) -> Sequence[Sequence[SequenceValue]]:
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
