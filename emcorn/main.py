import logging
import optparse as op, os
import resource
import sys

from emcorn.arbiter import Arbiter
from emcorn.logging import log, configure as configure_log, add_handler
from emcorn import util

UMASK = 0
MAXFD = 1024

def options():
    return [
        op.make_option('--host', dest='host', default='127.0.0.1', help='监听IP，默认: [%default]'),
        op.make_option('--port', dest='port', default='8089', type='int', help='监听端口，默认: [%default]'),
        op.make_option('--workers', dest='workers', default='1', type='int', help='开启工作进程数，默认: [%default]'),
        op.make_option('--log-level', dest='loglevel', default='info', help='日志输出级别[debug, info, warn, error, fatal]: [%default]'),
        op.make_option('--log-file', dest='logfile', default='-', help='日志输出文件，默认: [%default]'),
        op.make_option('-d', '--debug', dest='debug', default=False, action='store_true', help='开启调试模式，默认: [%default]. 开启后，只有一个 worker 进程'),
        op.make_option('-p', '--pid', dest='pidfile', help='后台进程PID文件'),
        op.make_option('-D', '--daemon', dest='daemon', action='store_true', help='以后台服务方式运行'),
    ]

def daemonize(opts):
    if 'EMCORN_FD' in os.environ:
        return

    if os.fork() == 0:
        os.setsid()
        if os.fork() == 0:
            os.umask(UMASK)
        else:
            os._exit(0)
    else:
       os._exit(0)
    
    for fd in range(0, util.get_maxfd()):
        try:
            os.close(fd)
        except OSError:
            pass

    os.open(util.DAEMON_REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)

def main(usage):
    parser = op.OptionParser(usage=usage, option_list=options())
    opts, args = parser.parse_args()

    print(emcorn_log())
    if opts.debug:
        if opts.workers > 1:
            log.info('debug mode, workers will be setted value 1')
        opts.workers = 1
    log.info(f'worker count:{opts.workers}')

    app = util.import_app(args[0])
    if opts.daemon:
        if opts.logfile == '-':
            log_file = f'{opts.pidfile}.log'
            log.info(f'emcorn is running background. more info at {log_file}')
            opts.logfile = log_file
        daemonize(opts)
    
    configure_log(opts)
    
    Arbiter(
        (opts.host, opts.port), opts.workers, app,
        debug=opts.debug, pidfile=opts.pidfile
    ).run()

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