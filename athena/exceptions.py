class AthenaException(Exception):
    def __init__(self, message):
        super().__init__(message)

class QuietException(Exception):
    def __init__(self, message: str | None=None):
        self.message = message
        if message is None:
            super().__init__(message)
        else:
            super().__init__()
