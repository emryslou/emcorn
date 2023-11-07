import logging

logger = logging.getLogger('emcorn')

def configure(opts):
    handlers = [
        logging.StreamHandler()
    ]
    loglevel = getattr(logging, opts.pop('loglevel', 'info').upper())
    logger.setLevel(loglevel)
    for handler in handlers:
        handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]%(message)s'))
        logger.addHandler(handler)


def get_logger():
    return logger