"""Command line interface used by click package to create `tasdmc` executable"""

try:
    from tasdmc.cli.group import cli
    import tasdmc.cli.commands  # noqa
except ModuleNotFoundError as e:
    print(f"'tasdmc' was not installed properly: some dependencies are missing: {e}")
    import sys

    sys.exit(1)


__all__ = [cli]
