import click

from typing import TypeVar, Sequence, Optional, Dict, Generator, Tuple, Any


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


def items_dot_notation(d: Dict) -> Generator[Tuple[str, Any], None, None]:
    """Generator yielding fully qualified dot notation keys with their values, e.g.

    >>> {
    ...       "nested":
    ...         {
    ...             "dict": {"one": 1, "two": 2},
    ...             "list": [4, 5, 6]
    ...         },
    ...     "top": "level"
    ... }

    will be turned into generator of

    >>> ("nested.dict.one", 1),
    >>> ("nested.dict.two", 2),
    >>> ("nested.list", [4, 5, 6]),  # no recursion into lists!
    >>> ("top", "level"),
    """
    for key, value in d.items():
        if isinstance(value, dict):
            for nested_key, nested_value in items_dot_notation(value):
                yield f"{key}.{nested_key}", nested_value
        else:
            yield key, value


NO_DEFAULT = object()
NO_SUCH_KEY = object()


def get_dot_notation(d: Dict, key: str, default: Optional[Any] = NO_DEFAULT) -> Any:
    """Utility function to get (possibly deeply nested) key from dict get nice error messages
    in case something is wrong.
    """
    level_keys = key.split('.')
    if not level_keys:
        raise ValueError('No key specified')

    traversed_level_keys = []
    current_value = d
    for level_key in level_keys:
        if not isinstance(current_value, dict):
            raise KeyError(
                f"Expected {'.'.join(traversed_level_keys)} to be dict with {level_key} key, "
                + f"found {current_value.__class__.__name__}",
            )
        current_value = current_value.get(level_key, NO_SUCH_KEY)
        if current_value is NO_SUCH_KEY:
            if default is NO_DEFAULT:
                raise KeyError(
                    f"Can't find top-level key '{level_key}'"
                    if not traversed_level_keys
                    else f"'{'.'.join(traversed_level_keys)}' does not contain required '{level_key}' key"
                )
            else:
                return default
        else:
            traversed_level_keys.append(level_key)

    return current_value


def set_dot_notation(d: Dict, key: str, value: Any):
    """Utility function to assign (possibly deeply nested) key in the dict"""
    level_keys = key.split('.')
    if not level_keys:
        raise ValueError('No key specified')
    n_levels = len(level_keys)

    traversed_keys = []
    subdict = d
    for i_level, level_key in enumerate(level_keys):
        if not isinstance(subdict, dict):
            raise KeyError(
                f"Expected {'.'.join(traversed_keys)} to be dict with {level_key} key, "
                + f"found {subdict.__class__.__name__}",
            )
        if i_level == n_levels - 1:
            subdict[level_key] = value
            return
        subsubdict = subdict.get(level_key, NO_SUCH_KEY)
        if subsubdict is NO_SUCH_KEY:
            subsubdict = dict()  # automatically appending keys
            subdict[level_key] = subsubdict
        subdict = subsubdict
        traversed_keys.append(level_key)

    return subdict
