import errno
import fcntl
import os
import select
import socket
import signal
import sys
import tempfile
import threading

from emcorn import http
from emcorn.logging import log
from emcorn.http.request import RequestError
from emcorn.util import import_app

class Worker(object):
    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "QUIT INT TERM TTIN TTOU".split()
    )

    def __init__(self, idx, ppid, sock, modname):
        self.id = idx
        self.ppid = ppid
        self.pid = '-'
        self.alive = True

        self.sock = sock
        self.address = sock.getsockname()
        self.app = import_app(modname)
        self.tmp = tempfile.TemporaryFile('w+t')
    
    def init_signal(self):
        map(lambda s: signal.signal(s, signal.SIG_DFL), self.signals)
        signal.signal(signal.SIGQUIT, self.sig_handle_quit)
        signal.signal(signal.SIGTERM, self.sig_handle_exit)
        signal.signal(signal.SIGINT, self.sig_handle_exit)
    
    def run(self):
        self.pid = os.getpid()
        self.init_signal()
        try:
            spinner = 0
            while self.alive:
                while self.alive:
                    ret = select.select([self.sock], [], [], 2.0)
                    if ret[0]:
                        break
                
                while self.alive:
                    try:
                        conn, addr = self.sock.accept()
                    except BlockingIOError:
                        break
                    except socket.error as err:
                        if err.errno != errno.EINTR:
                            raise err
                    try:
                        conn.setblocking(False)
                        self.handle(conn, addr)
                    finally:
                        conn.close()

                    spinner = (spinner + 1) % 2
                    os.fchmod(self.tmp.fileno(), spinner)
                # end while True
            # end while self.alive
        except KeyboardInterrupt:
            self.alive = False
    
    def quit(self):
        self.alive = False
    
    def handle(self, conn, client):
        fcntl.fcntl(conn.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        req = http.HttpRequest(conn, client, self.address)
        try:
            result = self.app(req.read(), req.start_response)
            res = http.HttpResponse(req, result)
            res.send()
            if req.should_close():
                req.close()
        except Exception as exc:
            req.close()
            log.error(f'{client}:request error {exc}')

    def sig_handle_quit(self, sig, frame):
        self.alive = False
    
    def sig_handle_exit(self, sig, frame):
        sys.exit(-1)

    def close(self):
        self.tmp.close()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<ppid:{self.ppid},pid:{self.pid},id:{self.id}>'
