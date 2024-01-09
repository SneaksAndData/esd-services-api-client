class FatalNexusError(BaseException):
    """
    Base exception class for all non-retryable application errors.
    """


class TransientNexusError(BaseException):
    """
    Base exception class for all retryable application errors.
    """
