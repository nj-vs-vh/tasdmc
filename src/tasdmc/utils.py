import click

from typing import TypeVar, Sequence, Optional


SequenceValue = TypeVar('SequenceValue')


def batches(seq: Sequence[SequenceValue], size: int) -> Sequence[Sequence[SequenceValue]]:
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


def user_confirmation(
    prompt: str, yes: Optional[str], no: Optional[str] = None, default: Optional[bool] = None
) -> bool:
    if yes is None and no is None:
        raise ValueError("At least one expected answer must be specified")
    answer_option_strs = []
    if yes is not None:
        yes_answer_str = click.style(yes, underline=True) if default is True else yes
        answer_option_strs.append(f'"{yes_answer_str}" to confirm')
    if no is not None:
        no_answer_str = click.style(no, underline=True) if default is False else no
        answer_option_strs.append(f'"{no_answer_str}" to decline')
    answers_str = ', '.join(answer_option_strs)
    click.echo(f"{prompt} [{answers_str}]")
    while True:
        answer = input("> ")
        if answer == yes:
            return True
        elif answer == no:
            return False
        elif default is not None:
            return default
        click.echo(f"Unkwnown answer, expected answers are: {answers_str}")


def user_confirmation_destructive(run_name: str):
    return user_confirmation("This is a destructive action!", yes=run_name, default=False)
