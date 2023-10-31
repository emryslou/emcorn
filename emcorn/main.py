import optparse as op

from emcorn.arbiter import Arbiter
from emcorn.logging import log

def options():
    return [
        op.make_option('--host', dest='host', default='127.0.0.1', help='监听IP，默认: [%default]'),
        op.make_option('--port', dest='port', default='8089', type='int', help='监听端口，默认: [%default]'),
        op.make_option('--workers', dest='workers', default='1', type='int', help='开启工作进程数，默认: [%default]'),
    ]


def main(usage):
    parser = op.OptionParser(usage=usage, option_list=options())
    opts, args = parser.parse_args()
    
    arbiter = Arbiter((opts.host, opts.port), opts.workers, '')
    log.info('Emcorn starting ...')
    log.info(f'listening: {opts.host}:{opts.port}')
    log.info(f'worker count:{opts.workers}')
    arbiter.run()
