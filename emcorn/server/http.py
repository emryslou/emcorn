import errno
import os
import socket
import sys
import time

class Worker(object):
    def __init__(self, nr, tmp):
        self.nr = nr
        self.tmp = tmp

class HttpServer(object):
    
    def __init__(
        self, app, worker_processes, timeout=60,
        init_listeners = [],
        pidfile=None, logging_handler = None, **opts
    ):
        pass

    def listen(self, addr, opts):
        tries = 5
        delay = 0.5
        for _idx in range(tries):
            try:
                pass
            except socket.error as exc:
                if e[0] == errno.EADDRINUSE:
                    # todo: logging
                    pass
                
                if _idx < tries:
                    # todo: logging
                    pass
                time.sleep(delay)
    
    def join(self):
        self.init_pipe()
        try:
            os.waitid(-1, 0)
        except KeyboardInterrupt:
            # kill_all_workers
            sys.exit()
