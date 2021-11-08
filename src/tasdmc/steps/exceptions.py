class FilesCheckFailed(Exception):
    """Generic exception for Files.assert_files_are_ready method and related functions"""

    pass


class BadDataFiles(Exception):
    pass


class HashComputationFailed(Exception):
    pass
