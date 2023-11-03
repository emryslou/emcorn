from datetime import datetime
import errno
import fcntl
import os
import select, socket, signal, sys
import tempfile, time, threading, traceback

from emcorn import http, util
from emcorn.logging import log
from emcorn.http.request import RequestError
from emcorn.util import close, close_on_exec, import_app, write_lines, write_nonblock

class Worker(object):
    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2".split()
    )

    def __init__(self, idx, ppid, sock, app, pipes, timeout, debug=False):
        self.alive = True
        self.nr = 0

        self.id = idx
        self.ppid = ppid
        self.pid = '-'
        self.timeout = timeout
        self.debug = debug
        self.sock = sock
        self.pipes = pipes
        self.address = sock.getsockname()
        self.app = app

        fd, tmpname = tempfile.mkstemp()
        self.tmp = os.fdopen(fd, 'r+b')
        self.tmpname = tmpname

        util.close_on_exec(sock)
        util.close_on_exec(fd)
        util.set_non_blocking(self.sock)
        [util.close_on_exec(p) for p in self.pipes]

    def init_signal(self):
        [ signal.signal(s, signal.SIG_DFL) for s in self.signals]
        
        signal.signal(signal.SIGQUIT, self.sig_handle_quit)
        signal.signal(signal.SIGHUP, self.sig_handle_quit)
        signal.signal(signal.SIGTERM, self.sig_handle_exit)
        signal.signal(signal.SIGINT, self.sig_handle_exit)
        signal.signal(signal.SIGUSR1, self.sig_handle_usr1)
        signal.signal(signal.SIGUSR2, self.sig_handle_quit)
    
    def _fchmod(self):
        try:
            os.write(self.tmp.fileno(), b'.')
        except:
            pass
        
    def run(self):
        self.pid = os.getpid()
        self.init_signal()
        self.nr = 0
        try:
            while self.alive:
                self.nr = 0
                while self.alive:
                    self.nr = 0
                    self._fchmod()
                    try:
                        conn, addr = self.sock.accept()
                        _start = datetime.now().timestamp()
                        self.handle(conn, addr, _start)
                        self.nr += 1
                    except BlockingIOError:
                        break
                    except socket.error as err:
                        if err.errno in [errno.EAGAIN, errno.ECONNABORTED]:
                            break
                        raise Exception(err)
                    if self.nr == 0:
                        break
                
                while self.alive:
                    self._fchmod()
                    try:
                        ret = select.select([self.sock], [], [], self.timeout)
                        if ret[0]:
                            break
                    except select.error as err:
                        if err.errno == errno.EINTR:
                            break
                        elif err.errno == errno.EBADF:
                            return
                        raise
                # end while True
            # end while self.alive
        #end try
        except KeyboardInterrupt:
            self.alive = False

    def quit(self):
        self.alive = False
    
    def handle(self, conn, client, start_time):
        # fcntl.fcntl(conn.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        self.close_on_exec(conn)
        try:
            req = http.HttpRequest(conn, client, self.address, self.debug)
            try:
                res = self.app(req.read(), req.start_response)
                log.info('request: %s %s' % (self.id, req.parser._headers_dict.get('Trace', start_time)))
                res_handle = http.HttpResponse(conn, res, req, self.debug)
                res_handle.headers['elpased'] = '%f %s'% ((datetime.now().timestamp() - start_time) * 1000, 'ms')
                res_handle.send()
            except BaseException as e:
                exc = ''.join([traceback.format_exc()])
                msg = (
                        '<h1>Internal Server Error</h1>'
                        f'<h2>wsgi error: {e}</h2>'
                        f'<pre>{exc}</pre>'
                    )
                write_lines(conn, [
                    f'{req.parser.raw_version} 500 Internal Server Error',
                    'Connection: close\r\n',
                    'Content-Type: text/html\r\n',
                    'Content-Length: %s\r\n' % (str(len(msg))),
                    "\r\n",
                    msg
                ])
            #end try ... except
        except Exception as exc:
            try:
                write_nonblock(conn, b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
            except Exception as exc1:
                pass
            log.error(f'{client}:request error {exc}, stack:\n{traceback.format_exc()}')
            

    def sig_handle_quit(self, sig, frame):
        self.quit()
    
    def sig_handle_exit(self, sig, frame):
        self.quit()
        os._exit(-1)
    
    def sig_handle_usr1(self, sig, frame):
        self.nr = -65535
        try:
            [p.close() for p in self.pipes]
        except:
            pass

    def close(self):
        self.tmp.close()
        [p.close() for p in self.pipes]

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<ppid:{self.ppid},pid:{self.pid},id:{self.id}>'
