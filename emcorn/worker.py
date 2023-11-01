import errno
import os
import select
import socket
import signal
import sys
import tempfile
import threading

from emcorn import http
from emcorn.logging import log
from emcorn.util import import_app


class SubWorker(threading.Thread):
    def __init__(self, worker, target, args, kwargs):
        super().__init__(target=target, args=args, kwargs=kwargs)
        self.worker = worker
        self.worker._threads.append(self)

    def run(self):
        try:
            if self._target is not None:
                self._target(*self._args, **self._kwargs)
        finally:
            del self._target, self._args, self._kwargs
            self.worker._threads.remove(self)
            if len(self.worker._threads) < self.worker._max_threads:
                self.worker._event.set()

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
        
        self._threads = []
        self._max_threads = 1
        self._event = threading.Event()
    
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
                    ret = select.select([self.sock], [], [], 10.0)
                    if ret[0]:
                        break
                while self.alive:
                    try:
                        conn, addr = self.sock.accept()
                    except socket.error as err:
                        if err.errno in [errno.EAGAIN, errno.EINTR]:
                            break
                        raise err
                    try:
                        conn.setblocking(True)
                        if self._max_threads > 1:
                            while len(self._threads) >= self._max_threads:
                                self._event.wait(0.5)
                            _t = SubWorker(self, self.handle, args=(conn, addr), kwargs={})
                            _t.start()
                        else:
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
        req = http.HttpRequest(conn, client, self.address)
        result = self.app(req.read(), req.start_response)
        res = http.HttpResponse(req, result)
        res.send()
        if req.should_close():
            req.close()

    def sig_handle_quit(self, sig, frame):
        self.alive = False
    
    def sig_handle_exit(self, sig, frame):
        sys.exit(-1)

    def close(self):
        self.tmp.close()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}<ppid:{self.ppid},pid:{self.pid},id:{self.id}>'
