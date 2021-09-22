import yaml

from typing import Dict, Any, Optional


def read_config(filename: str = 'config.yaml') -> Dict:
    with open(filename, 'r') as f:
        config = yaml.safe_load(f)
    return config


class ConfigKeyError(Exception):
    pass


def get_config_key(config: Dict, key: str, key_prefix: Optional[str] = None) -> Any:
    """Utility function to read (possibly deeply nested) keys from config dict and get nice error messages

    Args:
        config (Dict): loaded with read_config(filename)
        key (str): comma-separated list of keys from top to bottom, e.g. 'infiles.log10E.step'
        key_prefix (str): prefix added to the start of the key, e.g. for 'infiles' prefix any 'smth' key
                          becomes 'infiles.smth'

    Returns:
        Any: value in the specified key
    """
    if key_prefix is not None:
        key = key_prefix + '.' + key
    level_keys = key.split('.')
    traversed_level_keys = []

    current_value = config
    for level_key in level_keys:
        current_value = current_value.get(level_key)
        if current_value is None:
            raise ConfigKeyError(
                f"Config does not contain top-level '{level_key}' key"
                if not traversed_level_keys
                else f"Subconfig '{'.'.join(traversed_level_keys)}' does not contain required '{level_key}' key"
            )
        traversed_level_keys.append(level_key)

    return current_value
