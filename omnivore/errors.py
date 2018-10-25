class OmnivoreError(RuntimeError):
    """Base class for all errors custom to Omnivore
    """
    pass


class EmulatorError(OmnivoreError):
    """Base class for all emulation errors
    """
    pass


class UnknownEmulatorError(EmulatorError):
    """Raised when the requested emulator is not available
    """
    pass


class EmulatorInUseError(EmulatorError):
    """Raised when the requested emulator already has an active instance. Most
    emulators' low-level code doesn't allow for multiple concurrently-running
    emulation processes.
    """
    pass


class FrameNotFinishedError(EmulatorError):
    """Raised when an operation that must occur between frames is
    attempted while in the middle of a frame.
    """
    pass


class UnknownAssemblerError(OmnivoreError):
    """Raised when the requested assembler is not available
    """
    pass
