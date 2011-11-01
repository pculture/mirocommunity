class LocaltvException(Exception):
    """Base class for :mod:`localtv` exceptions."""
    pass


class InvalidVideo(LocaltvException):
    """
    Raised if a :class:`.Video` instance can't be created from a
    :class:`vidscraper.suites.base.Video` instance.

    """
    pass


class CannotOpenImageUrl(LocaltvException):
    """Raised if a thumbnail cannot be processed."""
    pass
