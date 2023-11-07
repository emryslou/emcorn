import optparse as op

from nobody import NoBody
from logger import logger, configure as configure_logger
def app(environ, start_response):    
    if environ['PATH_INFO'] == '/js/hello':
        start_response('200 OK', [
            ('Content-Type', 'application/javascript'),
            ('Content-Length', '21')
        ])
        return [
            b'window.alert(\'abc\')'
        ]
    elif environ['PATH_INFO'] == '/favicon.ico':
        start_response('200 OK', [
            # ('Content-Type', 'image/png'),
            ('Content-Length', '910')
            
        ])
        return [
            b'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAlJJREFUOE+dk1tI03EUxz+/ba1NX/7oFAsrXTIsEQ21aJSgGQiuICrqQXwpLfShR4OCIOqxB6EoLIpeulAY2CgvmeEgygsrynJiuvCyUFzetuXlv19staEbgfR7O5fvh3PO7xxBzJM9h3chgjVISoGMv2E3gtdITaMoanauloiIId8eN6IPNCA5DUT9sXwEd1gynhPWJ4FQLJwYFut+tbhG5ovff/SSpOgps6Zi2KiJ6r1+PWpQYEpcRCC6WDGUhyB/AL22xrn5leqG+984uC+VkVEf7nE/9dUWJhcM3OvOxBtMR6vRYlgZo6rIjdm0cFsU2mtEuGeCfavL9gdUhr77sGxXuNKei8V6lHSzBa0Ao89DU9NDzpc4pWJUC4Tstd1EcjZSa6tjkmdtE9RVmgkYM+jwVrCntCIszk7WYdDB4xdvME7ZOZI/fkvIHpsLsEQA1+4O4Rqep3RvCslZBbj0J8gttEbFA9Mq/Z8/0d35kgOWqcEQYBHQRwDNHT+wd3o4czKTxJStPBgsoe5UJQadICT2LUveddjpc7ziepV3KQ4gJUz/XMKUpEcCNxxZJGwqZlvubgKqhqH+D/jdnbS3OXh+OTkMWNNC7GItqxpaB9JwjimoUpCTNoctZ4JDFz00XUoZjBtiLOBfdln9JI8umEJDjP/GkGh41Ifzy2x40/J3Kpi3JKxhhQBXq5TC6CIhqV6d8bRlgiRlQ9jlnVnmWPnmOMDMrKqsWWWELF5XC1J05dd6LDops//7mHJqh78ateTFXd16z3lHXkFfgo79vwFggwNS3FYxUQAAAABJRU5ErkJggg=='
        ]
    else:
        start_response('200 OK', [
            ('Content-Type', 'text/html'),
        ])
        return [
            b'<h1>hello</h1>',
            b'<script src="/js/hello"></script>'
        ]

def options():
    return [
        op.make_option('--host', dest='host', default='127.0.0.1', help='监听IP，默认: [%default]'),
        op.make_option('--port', dest='port', default='8089', type='int', help='监听端口，默认: [%default]'),
        op.make_option('--workers', dest='workers', default='1', type='int', help='开启工作进程数，默认: [%default]'),
        op.make_option('--log-level', dest='loglevel', default='info', help='日志输出级别[debug, info, warn, error, fatal]: [%default]'),
    ]

def main():
    parser = op.OptionParser(usage="%prog [Options] APP_MODULE", option_list=options())
    opts, args = parser.parse_args()
    configure_logger(dict(loglevel=opts.loglevel))

    logger.info('emcorn start ...')
    NoBody(**dict(host=opts.host,port=opts.port,processes=opts.workers, app=app)).run()

main()
