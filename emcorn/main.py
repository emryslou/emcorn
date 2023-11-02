import logging
import optparse as op

from emcorn.arbiter import Arbiter
from emcorn.logging import log, configure as configure_log
from emcorn.util import import_app

def options():
    return [
        op.make_option('--host', dest='host', default='127.0.0.1', help='监听IP，默认: [%default]'),
        op.make_option('--port', dest='port', default='8089', type='int', help='监听端口，默认: [%default]'),
        op.make_option('--workers', dest='workers', default='1', type='int', help='开启工作进程数，默认: [%default]'),
        op.make_option('--log-level', dest='loglevel', default='info', help='日志输出级别[debug, info, warn, error, fatal]: [%default]'),
        op.make_option('--log-file', dest='logfile', default='-', help='日志输出文件，默认: [%default]'),
    ]


def main(usage):
    parser = op.OptionParser(usage=usage, option_list=options())
    opts, args = parser.parse_args()
    configure_log(opts)

    print(emcorn_log())
    log.info(f'listening: {opts.host}:{opts.port}')
    log.info(f'worker count:{opts.workers}')

    app = import_app(args[0])
    arbiter = Arbiter((opts.host, opts.port), opts.workers, app)
    arbiter.run()


def emcorn_log():
    return """

 /$$$$$$$$                                                      
| $$_____/                                                      
| $$       /$$$$$$/$$$$   /$$$$$$$  /$$$$$$   /$$$$$$  /$$$$$$$ 
| $$$$$   | $$_  $$_  $$ /$$_____/ /$$__  $$ /$$__  $$| $$__  $$
| $$__/   | $$ \ $$ \ $$| $$      | $$  \ $$| $$  \__/| $$  \ $$
| $$      | $$ | $$ | $$| $$      | $$  | $$| $$      | $$  | $$
| $$$$$$$$| $$ | $$ | $$|  $$$$$$$|  $$$$$$/| $$      | $$  | $$
|________/|__/ |__/ |__/ \_______/ \______/ |__/      |__/  |__/
                                                                
                                                                
    """