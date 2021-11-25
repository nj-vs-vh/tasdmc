class ConfigNotReadError(Exception):
    pass


class BadConfigError(Exception):
    pass


class ConfigKeyError(BadConfigError, KeyError):
    pass


class BadConfigValue(BadConfigError, ValueError):
    pass
