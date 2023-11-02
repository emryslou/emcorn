import errno
import fcntl
import os
import select
import socket
import signal
import sys
import tempfile
import time
import threading

from emcorn import http
from emcorn.logging import log
from emcorn.http.request import RequestError
from emcorn.util import import_app, write_nonblock

class Worker(object):
    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "HUP QUIT INT TERM TTIN TTOU USR1 USR2".split()
    )

    def __init__(self, idx, ppid, sock, app):
        self.id = idx
        self.ppid = ppid
        self.pid = '-'
        self.alive = True

        fd, tmpname = tempfile.mkstemp()
        self.tmp = os.fdopen(fd, 'r+b')
        self.tmpname = tmpname
        
        self.close_on_exec(sock)
        self.close_on_exec(fd)

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
    
    def run(self):
        self.pid = os.getpid()
        self.init_signal()
        try:
            spinner = 0
            while self.alive:
                while self.alive:
                    try:
                        ret = select.select([self.sock], [], [], 3.0)
                        if ret[0]:
                            break
                    except select.error as err:
                        if err.errno == errno.EINTR:
                            break
                        raise
                
                while self.alive:
                    try:
                        accept_res = self.sock.accept()
                        if accept_res is None:
                            break
                        conn, addr = accept_res
                        conn.setblocking(False)
                        self.handle(conn, addr)
                    except BlockingIOError:
                        break
                    except socket.error as err:
                        if err.errno in [errno.EAGAIN, errno.ECONNABORTED]:
                            break
                        raise Exception(err)

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
            req = http.HttpRequest(conn, client, self.address)
            result = self.app(req.read(), req.start_response)
            http.HttpResponse(conn, result, req).send()
        except Exception as exc:
            write_nonblock(conn, b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
            log.error(f'{client}:request error {exc}')
            import traceback
            traceback.print_exc()

    def sig_handle_quit(self, sig, frame):
        self.alive = False
    
    def sig_handle_exit(self, sig, frame):
        sys.exit(-1)

    def close(self):
        self.tmp.close()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<ppid:{self.ppid},pid:{self.pid},id:{self.id}>'
