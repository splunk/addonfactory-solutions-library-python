class ConfManagerException(Exception):
    """Exception raised by ConfManager class."""

    pass


class ConfStanzaNotExistException(Exception):
    """Exception raised by ConfFile class."""

    pass


class InvalidPortError(ValueError):
    """Exception raised when an invalid proxy port is provided."""

    pass


class InvalidHostnameError(ValueError):
    """Exception raised when an invalid proxy hostname is provided."""

    pass
