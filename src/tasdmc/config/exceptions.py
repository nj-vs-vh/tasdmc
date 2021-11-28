class ConfigNotReadError(Exception):
    pass


class BadConfigError(Exception):
    pass


class BadConfigValue(BadConfigError, ValueError):
    pass
