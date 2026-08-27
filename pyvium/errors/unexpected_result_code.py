'''Error for a DLL result code outside the set PYVIUM maps.'''


class UnexpectedResultCodeError(Exception):
    '''Raised when a DLL setter returns a result code PYVIUM does not model.

    The DLL convention is 0 for success, so a non-zero code means the command did
    not succeed. -1, 1, 2 and 3 map to their own typed exceptions; any other value
    means IviumSoft reported something this wrapper has not seen, and it is
    surfaced rather than assumed to be success.

    result_code carries the offending value, so a caller can branch on it or
    report it without parsing the message.
    '''

    def __init__(self, result_code: int, context: str = ""):
        self.result_code = result_code
        self.context = context
        suffix = f": {context}" if context else ""
        self.message = (
            f"IviumSoft returned an unrecognised result code {result_code} "
            f"(expected 0, -1, 1, 2 or 3){suffix}")
        super().__init__(self.message)
