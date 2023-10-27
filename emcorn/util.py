import logging

class NullHandler(logging.Handler):
    def emmit(self, record):
        pass
