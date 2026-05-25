class InvalidStateError(Exception):
    '''Raised when the device is in a state that prevents executing the command.

    Maps to DLL result code 3. The command is valid, but the device's current
    operating state does not allow it (e.g. trying to set a potential while a
    method is already running, or changing a range before connecting the cell).
    '''

    def __init__(self, message="The device is in an invalid state for this command."):
        self.message = message
        super().__init__(self.message)
