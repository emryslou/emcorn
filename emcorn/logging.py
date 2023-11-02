import logging

__all__ = [
    'log', 'configure'
]

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s]:%(message)s')
log = logging.getLogger('emcorn')

def configure(opts):
    handlers = []
    if opts.logfile != '-':
        handlers.append(logging.FileHandler(opts.logfile))
    
    loglevel = logging.getLevelName(opts.loglevel.upper())

    log.setLevel(loglevel)
    for h in handlers:
        h.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]:%(message)s'))
        log.addHandler(h)
