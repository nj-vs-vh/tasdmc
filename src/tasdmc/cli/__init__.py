"""Command line interface used by click package to create `tasdmc` executable"""

try:
    from tasdmc.cli.group import cli
    import tasdmc.cli.commands  # noqa
except ModuleNotFoundError:
    print("'tasdmc' was not installed properly: some dependencies are missing")
    import sys

    sys.exit(1)


__all__ = [cli]
