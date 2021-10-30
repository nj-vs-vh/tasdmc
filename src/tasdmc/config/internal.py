import yaml
from pathlib import Path

from typing import Optional, Dict, Any


_config: Optional[Dict[str, Any]] = None


def load(filename: str):
    global _config
    with open(filename, 'r') as f:
        _config = yaml.safe_load(f)


def dump(filename: Path):
    with open(filename, 'w') as f:
        yaml.dump(_config, f, sort_keys=False)


def get_config():
    return _config
