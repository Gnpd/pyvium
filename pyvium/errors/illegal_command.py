class IllegalCommandError(Exception):
    '''Raised when the device firmware cannot execute the command in its current state.

    Maps to DLL result code 1. Typical causes:
    - The device is in a mode that does not support this command.
    - A required precondition (e.g. cell on, specific connection mode) is not met.
    '''

    def __init__(self, message="The command is not available in the current device state."):
        self.message = message
        super().__init__(self.message)
