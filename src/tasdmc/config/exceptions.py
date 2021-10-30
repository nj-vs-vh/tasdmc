class ConfigNotReadError(Exception):
    pass


class ConfigKeyError(KeyError):
    pass


class BadConfigValue(ValueError):
    pass
