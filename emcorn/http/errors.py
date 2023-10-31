class RequestError(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason

        super().__init__(self, (status, reason))
