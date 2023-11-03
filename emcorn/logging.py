import logging
import os

__all__ = [
    'log', 'configure'
]

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s]:%(message)s')
log = logging.getLogger('emcorn')

def configure(opts):
    handlers = []
    if opts.logfile != '-':
        handlers.append(logging.FileHandler(opts.logfile))
    
    _loglevel = 'info'
    if 'LOG_LEVEL' in os.environ:
        _loglevel = os.environ['LOG_LEVEL'].upper()
        del os.environ['LOG_LEVEL']
    else:
        _loglevel = opts.loglevel.upper()
    
    loglevel = logging.getLevelName(opts.loglevel.upper())

    log.setLevel(loglevel)
    for h in handlers:
        h.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]:%(message)s'))
        log.addHandler(h)

def add_handler(handler):
    handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]:%(message)s'))
    log.addHandler(handler)