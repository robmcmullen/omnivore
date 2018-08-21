class Omni8bitError(RuntimeError):
    """Base class for all errors custom to Omni8bit
    """
    pass


class UnknownEmulatorError(Omni8bitError):
    """Raised when the requested emulator is not available
    """
    pass


class FrameNotFinishedError(Omni8bitError):
    """Raised when an operation that must occur between frames is
    attempted while in the middle of a frame.
    """
    pass
