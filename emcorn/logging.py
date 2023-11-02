import logging

__all__ = [
    'log',
]

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s]:%(message)s')
log = logging.getLogger('emcorn')
