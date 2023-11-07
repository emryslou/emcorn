class EmcornException(Exception):
    pass

class EmHttpException(EmcornException):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        super().__init__((status, reason))

class HttpParseError(EmHttpException):
    def __init__(self, reason = '', status = 400):
        super().__init__(status, reason)