import errno
import fcntl
import os
import select, socket, signal, sys
import tempfile, time, threading, traceback

from emcorn import http
from emcorn.logging import log
from emcorn.http.request import RequestError
from emcorn.util import import_app, write_lines, write_nonblock, close

class Worker(object):
    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2".split()
    )

    def __init__(self, idx, ppid, sock, app, timeout, debug=False):
        self.id = idx
        self.ppid = ppid
        self.pid = '-'
        self.alive = True
        self.timeout = timeout
        self.debug = debug

        fd, tmpname = tempfile.mkstemp()
        self.tmp = os.fdopen(fd, 'r+b')
        self.tmpname = tmpname
        
        self.close_on_exec(sock)
        self.close_on_exec(fd)

        sock.setblocking(False)
        self.sock = sock
        self.address = sock.getsockname()
       
        self.app = app
    
    def close_on_exec(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(fd, fcntl.F_SETFL, flags) # ????

    def init_signal(self):
        [ signal.signal(s, signal.SIG_DFL) for s in self.signals]
        
        signal.signal(signal.SIGQUIT, self.sig_handle_quit)
        signal.signal(signal.SIGHUP, self.sig_handle_quit)
        signal.signal(signal.SIGTERM, self.sig_handle_exit)
        signal.signal(signal.SIGINT, self.sig_handle_exit)
        signal.signal(signal.SIGUSR1, self.sig_handle_quit)
        signal.signal(signal.SIGUSR2, self.sig_handle_quit)
    
    def _fchmod(self):
        try:
            os.write(self.tmp.fileno(), b'.')
        except:
            pass
        
    def run(self):
        self.pid = os.getpid()
        self.init_signal()
        try:
            while self.alive:
                nr = 0
                
                while self.alive:
                    self._fchmod()
                    try:
                        conn, addr = self.sock.accept()
                        self.handle(conn, addr)
                        nr += 1
                    except BlockingIOError:
                        break
                    except socket.error as err:
                        if err.errno in [errno.EAGAIN, errno.ECONNABORTED]:
                            break
                        raise Exception(err)
                    if nr == 0:
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
        except KeyboardInterrupt:
            self.alive = False
        log.info(f'{self} done ... ')
    
    def quit(self):
        self.alive = False
    
    def handle(self, conn, client):
        # fcntl.fcntl(conn.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        self.close_on_exec(conn)
        try:
            req = http.HttpRequest(conn, client, self.address, self.debug)
            try:
                res = self.app(req.read(), req.start_response)
                http.HttpResponse(conn, res, req, self.debug).send()
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
                
        except Exception as exc:
            try:
                write_nonblock(conn, b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
                close(conn)
            except Exception as exc1:
                log.error(f'What the f**king, sending server\'s error msg happens some error: {exc1}')
                pass
            log.error(f'{client}:request error {exc}')
            traceback.print_exc()

    def sig_handle_quit(self, sig, frame):
        self.alive = False
    
    def sig_handle_exit(self, sig, frame):
        sys.exit(-1)

    def close(self):
        self.tmp.close()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<ppid:{self.ppid},pid:{self.pid},id:{self.id}>'
